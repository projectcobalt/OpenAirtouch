"""Adaptive strategy decision helpers."""

from __future__ import annotations

from typing import Any

from ..session.queue import TransactionSpec
from .adaptive_config import strategy_uses_mpc
from .adaptive_intent import _mode_intent_status, _proposal_status, _title_text
from .adaptive_model import AdaptiveDevice
from .adaptive_runtime_state import (
    _ac_name,
    _clamp_setpoint,
    _cooling_for_mode,
    _group_name,
    _groups_for_ac,
    _has_active_zone_for_ac,
    _number,
)
from .adaptive_signals import (
    AcTelemetrySignal,
    ClimateSignal,
    SolarSignal,
    WeatherSignal,
    _append_weather_recommendations,
    _forecast_step_for_control,
    _forecast_values_for_control,
    _indoor_allows_relax,
    _weather_opportunity,
)
from .adaptive_zone_call import zone_call_status


TOUCHPAD_2_SENSOR = 0x91


class AdaptiveStrategyMixin:
    def _recommend_action(
        self,
        device: AdaptiveDevice,
        ac: dict[str, Any],
        outside: float,
        weather: WeatherSignal,
        solar: SolarSignal,
        telemetry: AcTelemetrySignal,
        climate: ClimateSignal,
        thermal_intent: Any,
        status: dict[str, Any],
    ) -> None:
        mode_intent = thermal_intent.mode_intent
        ac_status = ac.get("status") or {}
        setpoint = _number(ac_status.get("setpoint"))
        cooling = thermal_intent.cooling if thermal_intent.cooling is not None else mode_intent.mode != 1
        opportunity_cooling = _cooling_for_mode(mode_intent.current_mode, default=cooling)
        opportunity = _weather_opportunity(outside, setpoint, opportunity_cooling, weather, climate)
        target: int | None = None
        forecast_target: int | None = None
        proposal = None
        if strategy_uses_mpc(self.config.control_strategy) and mode_intent.mode in (1, 4):
            target = thermal_intent.setpoint
            proposal = self._mpc_proposal(device, target, cooling, outside, weather, solar, telemetry, climate, advisory=True)
        hybrid_status = None
        if self.config.control_strategy == "hybrid" and target is not None:
            controlled_rooms = tuple(room for room in device.rooms if room.active and room.configured_control and room.temperature is not None)
            hybrid_status = self._hybrid_shadow_status(controlled_rooms, target, cooling, proposal)
        status["evaluations"][-1].update(_recommend_evaluation_status(
            target=target,
            forecast_target=forecast_target,
            opportunity=opportunity,
            weather_intent=self._weather_intent_status(device.ac_id, opportunity, None, {}, opportunity_cooling),
            mode_intent=mode_intent,
            air_quality=self._air_quality_status(device, climate, mode_intent),
            outside_air=self._outside_air_status(mode_intent),
            zone_call_state=zone_call_status(device.rooms, thermal_intent.cooling),
            proposal=proposal,
            hybrid=hybrid_status,
            solar=solar,
            climate=climate,
            cooling=cooling,
        ))
        name = _ac_name(device.ac_id, ac)
        _append_weather_recommendations(name, opportunity, status)
        if proposal is not None:
            if proposal.source in {"mpc", "zone"}:
                status["recommendations"].append(
                    f"{name}: Recommended Target: {proposal.target}° "
                    f"(Confidence {round(proposal.confidence * 100)}%, Action {_title_text(proposal.action)})"
                )
                if hybrid_status is not None and hybrid_status["damper_percentages"]:
                    damper_text = ", ".join(
                        f"Zone {int(group_id) + 1} {percent}%"
                        for group_id, percent in sorted(hybrid_status["damper_percentages"].items(), key=lambda item: int(item[0]))
                    )
                    status["recommendations"].append(f"{name}: Damper Plan: {damper_text}")
            elif proposal.source == "learning":
                status["recommendations"].append(f"{name}: {_learning_recommendation(proposal)}")

    def _weather_action(
        self,
        state: dict[str, Any],
        ac_id: int,
        ac: dict[str, Any],
        outside: float,
        weather: WeatherSignal,
        climate: ClimateSignal,
        thermal_intent: Any,
        status: dict[str, Any],
        now: float,
        planned_power_off: set[int],
    ) -> list[TransactionSpec]:
        mode_intent = thermal_intent.mode_intent
        ac_status = ac.get("status") or {}
        setpoint = _number(ac_status.get("setpoint"))
        if setpoint is None:
            return []
        cooling = _cooling_for_mode(mode_intent.current_mode, default=mode_intent.mode != 1)
        opportunity = _weather_opportunity(outside, setpoint, cooling, weather, climate)
        suspension = self._weather_suspension(ac_id)
        should_stop = opportunity["outside_favourable"]
        status["evaluations"][-1].update(_weather_evaluation_status(
            opportunity=opportunity,
            weather_intent=self._weather_intent_status(ac_id, opportunity, suspension, state, cooling),
            mode_intent=mode_intent,
        ))
        name = _ac_name(ac_id, ac)
        if suspension is not None:
            if ac_status.get("power_on") is True:
                self._clear_weather_suspension(ac_id)
                status["recommendations"].append(f"{name}: Weather Resume Cancelled: AC Power Changed Externally")
                status["evaluations"][-1]["weather_intent"] = self._weather_intent_status(
                    ac_id,
                    opportunity,
                    None,
                    state,
                    cooling,
                    cancelled_reason="ac_power_changed_externally",
                )
                return []
            if not _has_active_zone_for_ac(state, ac_id, ac):
                self._clear_weather_suspension(ac_id)
                status["recommendations"].append(f"{name}: Weather Resume Cancelled: No Zones Are On")
                status["evaluations"][-1]["weather_intent"] = self._weather_intent_status(
                    ac_id,
                    opportunity,
                    None,
                    state,
                    cooling,
                    cancelled_reason="no_active_zones",
                )
                return []
            if opportunity["recommend_off"]:
                _append_weather_recommendations(name, opportunity, status)
                status["recommendations"].append(f"{name}: AC Paused: Outside Air Can Carry The Load")
                return []
            if not self._mpc.compressor.can_power_on(ac_id, now, self.config.compressor_min_off_time):
                status["recommendations"].append(f"{name}: Weather Resume Held By Compressor Minimum Off Time")
                return []
            spec = self._send_ac_power(state, ac_id, True, status, now, key_prefix="weather_resume")
            if spec is None:
                return []
            self._clear_weather_suspension(ac_id)
            status["actions"].append(f"{name}: AC Resumed")
            status["evaluations"][-1]["weather_intent"] = self._weather_intent_status(
                ac_id,
                opportunity,
                None,
                state,
                cooling,
                resumed=True,
            )
            return [spec]
        if not should_stop:
            return []
        _append_weather_recommendations(name, opportunity, status)
        if self.config.mode != "adaptive":
            return []
        if not self._mpc.compressor.can_power_off(
            ac_id,
            now,
            self.config.compressor_min_run_time,
            planned_off=planned_power_off,
        ):
            status["recommendations"].append(f"{name}: Weather Off Held By Compressor Minimum Run Time")
            return []
        if not opportunity["indoor_comfort_allows"]:
            status["recommendations"].append(f"{name}: Weather Off Held By Indoor Temperature")
            return []
        if not opportunity["forecast_favourable"]:
            status["recommendations"].append(f"{name}: Weather Off Held By Forecast")
            return []
        spec = self._send_ac_power(state, ac_id, False, status, now, key_prefix="weather_suspend")
        if spec is None:
            return []
        self._record_weather_suspension(ac_id, opportunity, now, cooling)
        status["actions"].append(f"{name}: Turned AC Off")
        status["evaluations"][-1]["weather_intent"] = self._weather_intent_status(
            ac_id,
            opportunity,
            self._weather_suspension(ac_id),
            state,
            cooling,
        )
        planned_power_off.add(ac_id)
        return [spec]

    def _adaptive_action(
        self,
        state: dict[str, Any],
        device: AdaptiveDevice,
        ac: dict[str, Any],
        outside: float,
        weather: WeatherSignal,
        solar: SolarSignal,
        telemetry: AcTelemetrySignal,
        climate: ClimateSignal,
        thermal_intent: Any,
        status: dict[str, Any],
        now: float,
    ) -> list[TransactionSpec]:
        mode_intent = thermal_intent.mode_intent
        specs: list[TransactionSpec] = []
        ac_id = device.ac_id
        ac_status = ac.get("status") or {}
        cooling = thermal_intent.cooling if thermal_intent.cooling is not None else mode_intent.mode != 1
        forecast_target = None
        target = thermal_intent.setpoint
        if target is None:
            target = self._control_target(device, ac, outside, weather, climate, cooling)
        groups = _groups_for_ac(state, ac_id, ac)
        controlled_rooms = tuple(room for room in device.rooms if self._participating_room(room) and room.temperature is not None)
        controlled_group_ids = {room.id for room in controlled_rooms}
        proposal = self._mpc_proposal(device, target, cooling, outside, weather, solar, telemetry, climate) if mode_intent.mode in (1, 4) else None
        if proposal is not None:
            target = _clamp_setpoint(proposal.target, ac)
        name = _ac_name(ac_id, ac)
        status["evaluations"][-1].update(_zone_evaluation_status(
            target=target,
            forecast_target=forecast_target,
            mode_intent=mode_intent,
            air_quality=self._air_quality_status(device, climate, mode_intent),
            outside_air=self._outside_air_status(mode_intent),
            zone_call_state=zone_call_status(device.rooms, thermal_intent.cooling),
            proposal=proposal,
            solar=solar,
            climate=climate,
            cooling=cooling,
        ))
        outside_air_specs = self._outside_air_action(state, ac_id, status, now, mode_intent)
        if not controlled_rooms:
            if not mode_intent.outside_air_intent:
                specs.extend(self._restore_ac(state, ac_id, status, now))
                specs.extend(outside_air_specs)
                return specs
            mode_spec = self._set_ac_mode(state, ac_id, mode_intent, status, now)
            if mode_spec is not None:
                specs.append(mode_spec)
                status["actions"].append(f"{name}: Mode Changed: {mode_intent.name}")
            specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
            specs.extend(outside_air_specs)
            return specs
        for group_id, group in groups:
            if group_id not in controlled_group_ids:
                continue
            power_spec = self._set_group_power(state, group_id, True, status, now)
            if power_spec is not None:
                specs.append(power_spec)
                status["actions"].append(f"{_group_name(group_id, group)}: Zone Turned On")
        if controlled_group_ids and not device.power_on and self.config.allow_ac_power_on:
            power_spec = self._send_ac_power(state, ac_id, True, status, now, key_prefix="zone_available")
            if power_spec is not None:
                specs.append(power_spec)
                status["actions"].append(f"{name}: AC Made Available")
        mode_spec = self._set_ac_mode(state, ac_id, mode_intent, status, now)
        if mode_spec is not None:
            specs.append(mode_spec)
            status["actions"].append(f"{name}: Mode Changed: {mode_intent.name}")
        if mode_intent.mode not in (1, 4):
            specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
            specs.extend(outside_air_specs)
            return specs
        specs.extend(outside_air_specs)
        specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
        for group_id, group in groups:
            group_status = group.get("status") or {}
            if group_id not in controlled_group_ids:
                specs.extend(self._restore_group_power(state, group_id, status, now))
                specs.extend(self._restore_group_setpoint(state, group_id, status, now))
                continue
            group_setpoint = _number(group_status.get("setpoint"))
            if group_setpoint is None:
                continue
            if int(round(group_setpoint)) != target:
                spec = self._set_group_setpoint(state, group_id, target, status, now)
                if spec is not None:
                    specs.append(spec)
                    status["actions"].append(f"{_group_name(group_id, group)}: Setpoint Changed: {target}°")
            else:
                specs.extend(self._restore_group_setpoint(state, group_id, status, now))
        return specs

    def _hybrid_damper_action(
        self,
        state: dict[str, Any],
        device: AdaptiveDevice,
        ac: dict[str, Any],
        outside: float,
        weather: WeatherSignal,
        solar: SolarSignal,
        telemetry: AcTelemetrySignal,
        climate: ClimateSignal,
        thermal_intent: Any,
        status: dict[str, Any],
        now: float,
    ) -> list[TransactionSpec]:
        mode_intent = thermal_intent.mode_intent
        specs: list[TransactionSpec] = []
        ac_id = device.ac_id
        ac_status = ac.get("status") or {}
        cooling = thermal_intent.cooling if thermal_intent.cooling is not None else mode_intent.mode != 1
        forecast_target = None
        target = thermal_intent.setpoint
        if target is None:
            target = self._control_target(device, ac, outside, weather, climate, cooling)
        proposal = self._mpc_proposal(device, target, cooling, outside, weather, solar, telemetry, climate) if mode_intent.mode in (1, 4) else None
        if proposal is not None:
            target = _clamp_setpoint(proposal.target, ac)
        name = _ac_name(ac_id, ac)
        controlled_rooms = tuple(room for room in device.rooms if self._participating_room(room) and room.temperature is not None)
        controlled_group_ids = {room.id for room in controlled_rooms}
        control_plan = _hybrid_control_plan(
            controlled_rooms,
            target,
            cooling,
            proposal.power_fraction if proposal else 0.0,
            telemetry,
            max_boost_degrees=self.config.hybrid_max_boost_degrees,
        )
        control_temperature = control_plan["control_temperature"]
        status["evaluations"][-1].update(_hybrid_evaluation_status(
            target=target,
            forecast_target=forecast_target,
            mode_intent=mode_intent,
            air_quality=self._air_quality_status(device, climate, mode_intent),
            outside_air=self._outside_air_status(mode_intent),
            zone_call_state=zone_call_status(device.rooms, thermal_intent.cooling),
            proposal=proposal,
            control_temperature=control_temperature,
            control_plan=control_plan,
            solar=solar,
            climate=climate,
            cooling=cooling,
        ))
        outside_air_specs = self._outside_air_action(state, ac_id, status, now, mode_intent)
        if mode_intent.mode not in (1, 4):
            mode_spec = self._set_ac_mode(state, ac_id, mode_intent, status, now)
            if mode_spec is not None:
                specs.append(mode_spec)
                status["actions"].append(f"{name}: Mode Changed: {mode_intent.name}")
        if mode_intent.mode not in (1, 4):
            specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
            specs.extend(self._restore_ac_control_sensor(state, ac_id, status, now))
            specs.extend(self._restore_dampers_for_ac(state, ac_id, ac, status, now))
            specs.extend(outside_air_specs)
            return specs
        if not controlled_rooms:
            status["recommendations"].append(f"{name}: Hybrid Held: No Active Controlled Temperature Zones")
            specs.extend(self._restore_ac(state, ac_id, status, now))
            specs.extend(self._restore_dampers_for_ac(state, ac_id, ac, status, now))
            specs.extend(outside_air_specs)
            return specs
        if proposal is None:
            status["recommendations"].append(f"{name}: Hybrid Waiting For Forecast Proposal")
            specs.extend(self._restore_ac_control_sensor(state, ac_id, status, now))
            specs.extend(self._restore_dampers_for_ac(state, ac_id, ac, status, now))
            specs.extend(outside_air_specs)
            return specs
        if proposal.source not in {"mpc", "zone"}:
            status["recommendations"].append(f"{name}: Model Learning: Waiting Before Damper Control")
            specs.extend(self._restore_ac_control_sensor(state, ac_id, status, now))
            specs.extend(self._restore_dampers_for_ac(state, ac_id, ac, status, now))
            specs.extend(outside_air_specs)
            return specs
        groups = _groups_for_ac(state, ac_id, ac)
        for group_id, group in groups:
            if group_id not in controlled_group_ids:
                specs.extend(self._restore_group_power(state, group_id, status, now))
                if not (mode_intent.outside_air_intent and group_id in self.config.outside_air_zones):
                    specs.extend(self._restore_group_percentage(state, group_id, status, now))
                continue
            power_spec = self._set_group_power(state, group_id, True, status, now)
            if power_spec is not None:
                specs.append(power_spec)
                status["actions"].append(f"{_group_name(group_id, group)}: Zone Turned On")
            group_status = group.get("status") or {}
            current = _number(group_status.get("percentage"))
            if current is None:
                continue
            percent = _hybrid_damper_percent(
                proposal.zone_power_fractions.get(group_id, proposal.power_fraction),
                minimum_percent=self.config.hybrid_min_damper_percent,
                maximum_percent=self.config.hybrid_max_damper_percent,
                idle_percent=self.config.hybrid_idle_damper_percent,
            )
            status["evaluations"][-1]["hybrid"]["damper_percentages"][str(group_id)] = percent
            spec = self._set_group_percentage(state, group_id, percent, status, now)
            if spec is not None:
                specs.append(spec)
                status["actions"].append(f"{_group_name(group_id, group)}: Damper Changed: {percent}%")
        control_sensor_spec = self._set_ac_control_sensor(state, ac_id, TOUCHPAD_2_SENSOR, status, now)
        if control_sensor_spec is not None:
            specs.append(control_sensor_spec)
            status["actions"].append(f"{name}: Control Sensor Changed: Touchpad 2")
        if control_temperature is not None:
            temp_spec = self._set_touchpad_temperature(state, TOUCHPAD_2_SENSOR, control_temperature, status, now)
            if temp_spec is not None:
                specs.append(temp_spec)
                commanded_temp = int(round(control_temperature))
                status["actions"].append(f"{name}: Control Temperature Updated: {commanded_temp}°")
            status["evaluations"][-1]["hybrid"]["touchpad_temperature_commanded"] = temp_spec is not None
            status["evaluations"][-1]["hybrid"]["touchpad_temperature"] = int(round(control_temperature))
            status["evaluations"][-1]["hybrid"]["touchpad_sensor"] = TOUCHPAD_2_SENSOR
        else:
            status["evaluations"][-1]["hybrid"]["touchpad_temperature_note"] = "No Controlled Zone Temperatures Available"
        if controlled_group_ids and not device.power_on and self.config.allow_ac_power_on:
            power_spec = self._send_ac_power(state, ac_id, True, status, now, key_prefix="hybrid_available")
            if power_spec is not None:
                specs.append(power_spec)
                status["actions"].append(f"{name}: AC Made Available")
        mode_spec = self._set_ac_mode(state, ac_id, mode_intent, status, now)
        if mode_spec is not None:
            specs.append(mode_spec)
            status["actions"].append(f"{name}: Mode Changed: {mode_intent.name}")
        setpoint = _number(ac_status.get("setpoint"))
        if setpoint is not None and int(round(setpoint)) != target:
            spec = self._set_ac_setpoint(state, ac_id, target, status, now)
            if spec is not None:
                specs.append(spec)
                status["actions"].append(f"{name}: Setpoint Changed: {target}°")
        else:
            specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
        specs.extend(outside_air_specs)
        return specs

    def _hybrid_shadow_status(
        self,
        controlled_rooms: tuple[Any, ...],
        target: int,
        cooling: bool,
        proposal: Any,
    ) -> dict[str, Any]:
        power_fraction = proposal.power_fraction if proposal is not None else 0.0
        status = {
            "strategy": "hybrid",
            **_hybrid_control_plan(
                controlled_rooms,
                target,
                cooling,
                power_fraction,
                None,
                max_boost_degrees=self.config.hybrid_max_boost_degrees,
            ),
            "damper_percentages": {},
            "touchpad_temperature_commanded": False,
            "touchpad_temperature_note": "Recommend Mode Only",
        }
        if proposal is None:
            return status
        for room in controlled_rooms:
            status["damper_percentages"][str(room.id)] = _hybrid_damper_percent(
                proposal.zone_power_fractions.get(room.id, proposal.power_fraction),
                minimum_percent=self.config.hybrid_min_damper_percent,
                maximum_percent=self.config.hybrid_max_damper_percent,
                idle_percent=self.config.hybrid_idle_damper_percent,
            )
        return status



def _hybrid_damper_percent(power_fraction: float, *, minimum_percent: int, maximum_percent: int, idle_percent: int) -> int:
    fraction = _number(power_fraction)
    if fraction is None or fraction <= 0.0:
        return _clamp_int(idle_percent, 0, 100)
    minimum = _percent_to_fraction(minimum_percent)
    maximum = _percent_to_fraction(maximum_percent)
    damper = minimum + (maximum - minimum) * min(1.0, fraction)
    return _fraction_to_percent(damper)


def _hybrid_control_plan(
    rooms: tuple[Any, ...],
    target: int,
    cooling: bool,
    power_fraction: float,
    telemetry: Any,
    *,
    max_boost_degrees: int,
) -> dict[str, Any]:
    temperatures = [float(room.temperature) for room in rooms if room.temperature is not None]
    if not temperatures:
        return {
            "control_temperature": None,
            "control_temperature_source": None,
            "control_temperature_base": None,
            "comfort_delta": None,
            "boost_degrees": 0,
            "telemetry_work_fraction": None,
        }
    base = max(temperatures) if cooling else min(temperatures)
    comfort_delta = max(0.0, base - target) if cooling else max(0.0, target - base)
    planned_work = _clamp_fraction(power_fraction)
    observed_work = _telemetry_work_fraction(telemetry)
    boost = _hybrid_boost_degrees(comfort_delta, planned_work, observed_work, max_boost_degrees=max_boost_degrees)
    synthetic = base + boost if cooling else base - boost
    return {
        "control_temperature": round(synthetic, 1),
        "control_temperature_source": "worst_zone_temperature",
        "control_temperature_base": round(base, 1),
        "comfort_delta": round(comfort_delta, 1),
        "boost_degrees": boost,
        "telemetry_work_fraction": observed_work,
    }


def _hybrid_control_temperature(rooms: tuple[Any, ...], target: int, cooling: bool, power_fraction: float) -> float | None:
    return _hybrid_control_plan(rooms, target, cooling, power_fraction, None, max_boost_degrees=2)["control_temperature"]


def _hybrid_boost_degrees(comfort_delta: float, planned_work: float, observed_work: float | None, *, max_boost_degrees: int) -> int:
    if comfort_delta < 0.5 or comfort_delta >= 3.0:
        return 0
    boost = 1 if planned_work >= 0.75 else 0
    if planned_work >= 0.95 and comfort_delta <= 2.0:
        boost = 2
    if observed_work is not None:
        shortfall = planned_work - observed_work
        if shortfall >= 0.7:
            boost = max(boost, 2)
        elif shortfall >= 0.35:
            boost = max(boost, 1)
    return _clamp_int(boost, 0, max_boost_degrees)


def _telemetry_work_fraction(telemetry: Any) -> float | None:
    if telemetry is None or getattr(telemetry, "available", False) is not True:
        return None
    frequency = _number(getattr(telemetry, "frequency_hz", None))
    if frequency is not None:
        return round(_clamp_fraction(frequency / 100.0), 3)
    power = _number(getattr(telemetry, "power_w", None))
    if power is not None:
        return round(_clamp_fraction((power - 120.0) / 1680.0), 3)
    observed = getattr(telemetry, "observed_conditioning", None)
    if observed is True:
        return 0.5
    if observed is False:
        return 0.0
    return None


def _clamp_fraction(value: Any) -> float:
    number = _number(value)
    if number is None:
        return 0.0
    return max(0.0, min(1.0, float(number)))


def _recommend_evaluation_status(
    *,
    target: int | None,
    forecast_target: int | None,
    opportunity: dict[str, Any],
    weather_intent: dict[str, Any],
    mode_intent: Any,
    air_quality: dict[str, Any],
    outside_air: dict[str, Any],
    zone_call_state: dict[str, Any],
    proposal: Any,
    hybrid: dict[str, Any] | None,
    solar: SolarSignal,
    climate: ClimateSignal,
    cooling: bool,
) -> dict[str, Any]:
    relaxation_allowed = opportunity["indoor_comfort_allows"] if target is None else _indoor_allows_relax(climate.indoor_temperature, target, cooling)
    return {
        "target": target,
        "forecast_target": forecast_target,
        "weather_opportunity": opportunity,
        "weather_intent": weather_intent,
        "mode_intent": _mode_intent_status(mode_intent),
        "air_quality": air_quality,
        "outside_air": outside_air,
        "zone_call_state": zone_call_state,
        "mpc": _proposal_status(proposal),
        "hybrid": hybrid,
        "solar": _solar_status(solar),
        "relaxation_allowed": relaxation_allowed,
    }


def _weather_evaluation_status(*, opportunity: dict[str, Any], weather_intent: dict[str, Any], mode_intent: Any) -> dict[str, Any]:
    return {
        "target": None,
        "forecast_target": None,
        "weather_opportunity": opportunity,
        "weather_intent": weather_intent,
        "mode_intent": _mode_intent_status(mode_intent),
        "mpc": None,
        "hybrid": None,
        "relaxation_allowed": opportunity["indoor_comfort_allows"],
    }


def _zone_evaluation_status(
    *,
    target: int,
    forecast_target: int | None,
    mode_intent: Any,
    air_quality: dict[str, Any],
    outside_air: dict[str, Any],
    zone_call_state: dict[str, Any],
    proposal: Any,
    solar: SolarSignal,
    climate: ClimateSignal,
    cooling: bool,
) -> dict[str, Any]:
    return {
        "target": target,
        "forecast_target": forecast_target,
        "mode_intent": _mode_intent_status(mode_intent),
        "air_quality": air_quality,
        "outside_air": outside_air,
        "zone_call_state": zone_call_state,
        "mpc": _proposal_status(proposal),
        "solar": _solar_status(solar),
        "relaxation_allowed": _indoor_allows_relax(climate.indoor_temperature, target, cooling),
    }


def _hybrid_evaluation_status(
    *,
    target: int,
    forecast_target: int | None,
    mode_intent: Any,
    air_quality: dict[str, Any],
    outside_air: dict[str, Any],
    zone_call_state: dict[str, Any],
    proposal: Any,
    control_temperature: float | None,
    control_plan: dict[str, Any] | None,
    solar: SolarSignal,
    climate: ClimateSignal,
    cooling: bool,
) -> dict[str, Any]:
    status = _zone_evaluation_status(
        target=target,
        forecast_target=forecast_target,
        mode_intent=mode_intent,
        air_quality=air_quality,
        outside_air=outside_air,
        zone_call_state=zone_call_state,
        proposal=proposal,
        solar=solar,
        climate=climate,
        cooling=cooling,
    )
    status["hybrid"] = {
        "strategy": "hybrid",
        "control_temperature": control_temperature,
        "control_temperature_source": (control_plan or {}).get("control_temperature_source") if control_temperature is not None else None,
        "control_temperature_base": (control_plan or {}).get("control_temperature_base"),
        "comfort_delta": (control_plan or {}).get("comfort_delta"),
        "boost_degrees": (control_plan or {}).get("boost_degrees", 0),
        "telemetry_work_fraction": (control_plan or {}).get("telemetry_work_fraction"),
        "damper_percentages": {},
        "touchpad_temperature_commanded": False,
        "touchpad_temperature_note": None,
    }
    return status


def _solar_status(solar: SolarSignal) -> dict[str, Any]:
    return {
        "q_solar": solar.q_solar,
        "source": solar.source,
    }


def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = minimum
    return min(max(number, minimum), maximum)


def _fraction_to_percent(value: float) -> int:
    return _clamp_int(round(float(value) * 100.0), 0, 100)


def _percent_to_fraction(value: int) -> float:
    return _clamp_int(value, 0, 100) / 100.0
def _learning_recommendation(proposal: Any) -> str:
    action = _proposal_learning_action(proposal)
    if action == "cooling":
        return "Cooling Model Warming Up"
    if action == "heating":
        return "Heating Model Warming Up"
    if action == "idle":
        return "Thermal Model Warming Up"
    return "Model Learning: Waiting For More Samples"


def _proposal_learning_action(proposal: Any) -> str | None:
    forecast = getattr(proposal, "runtime_forecast", None)
    windows = getattr(forecast, "action_windows", None)
    if windows:
        action = windows[0].get("action") if isinstance(windows[0], dict) else None
        if isinstance(action, str) and action:
            return action
    action = getattr(proposal, "action", None)
    return action if isinstance(action, str) and action else None
