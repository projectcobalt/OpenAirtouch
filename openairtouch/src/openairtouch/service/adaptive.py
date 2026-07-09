"""Local weather-adaptive control policy inspired by the AT5 console."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from ..session.queue import TransactionSpec
from .adaptive_commands import AdaptiveCommandMixin
from .adaptive_config import (
    AdaptiveConfig,
    adaptive_public_config,
    strategy_uses_mpc,
    validated_adaptive_config,
    zone_id,
)
from .adaptive_contracts import build_adaptive_ui_contract
from .adaptive_evaluator import AdaptiveEvaluatorMixin
from .adaptive_intent import _intent_status
from .adaptive_mpc import AdaptiveMpcEngine, MpcInputs
from .adaptive_model import AdaptiveDevice, AdaptiveRoom
from .adaptive_restore import AdaptiveRestoreMixin
from .adaptive_runtime_state import (
    _ac_name,
    _clamp_setpoint,
    _group_for_id,
    _group_name,
    _has_active_zone_for_ac,
    _indexed,
    _mode_name,
    _number,
    _optional_mode,
)
from .adaptive_strategies import AdaptiveStrategyMixin
from .adaptive_signals import (
    AcTelemetrySignal,
    ClimateSignal,
    SolarSignal,
    WeatherSignal,
    _ac_telemetry_status,
    _forecast_step_for_control,
    _forecast_values_for_control,
    _weather_window_minutes,
)
from .adaptive_state import (
    active_ac_restore_ids,
    active_group_restore_ids,
    export_restore_state,
    export_weather_state,
    import_restore_records,
    import_weather_suspensions,
)
from .adaptive_zone_call import zone_call_status


@dataclass(frozen=True)
class AcModeIntent:
    mode: int | None
    name: str
    reason: str
    source: str
    current_mode: int | None = None
    outside_air_intent: bool = False
    ventilation_reason: str | None = None


@dataclass(frozen=True)
class ThermalIntent:
    strategy: str
    mode_intent: AcModeIntent
    cooling: bool | None
    setpoint: int | None
    setpoint_source: str | None
    setpoint_reason: str | None


class AdaptiveController(AdaptiveEvaluatorMixin, AdaptiveStrategyMixin, AdaptiveCommandMixin, AdaptiveRestoreMixin):
    def __init__(self, config: AdaptiveConfig = AdaptiveConfig()) -> None:
        self.config = validated_adaptive_config(config)
        self._next_check = 0.0
        self._last_command: dict[str, tuple[int | bool, float]] = {}
        self._restore_records: dict[str, dict[str, Any]] = {}
        self._weather_suspensions: dict[str, dict[str, Any]] = {}
        self._mpc = AdaptiveMpcEngine()
        self._compressor_groups = self.config.compressor_groups
        self._mpc.compressor.configure(self._compressor_groups)
        self._status: dict[str, Any] = self._empty_status()

    def status(self) -> dict[str, Any]:
        return dict(self._status)

    def update_config(self, values: dict[str, Any]) -> dict[str, Any]:
        data = {field: getattr(self.config, field) for field in self.config.__dataclass_fields__}
        for key in data:
            if key in values and values[key] is not None:
                data[key] = values[key]
        if "control_strategy" in values and "learning_mode" not in values:
            data["learning_mode"] = "control" if strategy_uses_mpc(str(data["control_strategy"]).lower()) else "off"
        self.config = validated_adaptive_config(AdaptiveConfig(**data))
        self._set_compressor_groups(self.config.compressor_groups)
        if self.config.mode != "adaptive" or self.config.control_strategy != "weather":
            self._weather_suspensions.clear()
        self._next_check = 0.0
        self._status = {**self._status, "config": self.public_config(), "mode": self.config.mode}
        return self.public_config()

    def public_config(self) -> dict[str, Any]:
        return adaptive_public_config(self.config)

    def export_learning(self) -> dict[str, Any]:
        return {
            **self._mpc.to_dict(),
            "restore_state": self.export_restore_state(),
            "weather_state": self.export_weather_state(),
        }

    def import_learning(self, payload: dict[str, Any]) -> None:
        self._mpc.load_dict(payload)
        self.import_restore_state(payload.get("restore_state") if isinstance(payload, dict) else None)
        self.import_weather_state(payload.get("weather_state") if isinstance(payload, dict) else None)
        self._status = {**self._status, "learning": self._mpc.status(time.monotonic())}

    def learning_status(self, *, now: float | None = None) -> dict[str, Any]:
        return self._mpc.status(time.monotonic() if now is None else now)

    def export_restore_state(self) -> dict[str, Any]:
        return export_restore_state(self._restore_records)

    def import_restore_state(self, payload: Any) -> None:
        records = import_restore_records(payload)
        if records is None:
            return
        self._restore_records = records

    def export_weather_state(self) -> dict[str, Any]:
        return export_weather_state(self._weather_suspensions)

    def import_weather_state(self, payload: Any) -> None:
        suspensions = import_weather_suspensions(payload)
        if suspensions is None:
            return
        self._weather_suspensions = suspensions

    def manage_learning(self, values: dict[str, Any]) -> dict[str, Any]:
        action = str(values.get("action") or "").lower()
        if action == "reset_all":
            self._mpc.reset_all()
        elif action == "reset_zone":
            self._mpc.reset_zone(zone_id(values.get("zone")))
        elif action == "accelerate_zone":
            self._mpc.set_accelerated_learning_at(
                zone_id(values.get("zone")),
                bool(values.get("enabled", True)),
                now=time.monotonic(),
            )
        else:
            raise ValueError("adaptive model action must be reset_all, reset_zone, or accelerate_zone")
        self._status = {**self._status, "learning": self._mpc.status(time.monotonic())}
        return self._status["learning"]

    def _set_compressor_groups(self, groups: tuple[tuple[int, ...], ...]) -> None:
        groups = tuple(tuple(group) for group in groups)
        if groups == self._compressor_groups:
            return
        self._compressor_groups = groups
        self._mpc.compressor.configure(groups)

    def _air_quality_status(self, device: AdaptiveDevice, climate: ClimateSignal, mode_intent: AcModeIntent) -> dict[str, Any]:
        humidity_high = (
            climate.humidity is not None
            and climate.humidity_source == "home_assistant_indoor"
            and climate.humidity >= self.config.dry_humidity_threshold
        )
        co2_high = climate.co2_ppm is not None and climate.co2_ppm >= self.config.co2_ventilation_threshold_ppm
        thermal_mode = mode_intent.mode in (1, 4)
        active_zone_ids = [
            int(room.id)
            for room in device.rooms
            if room.active and (room.control_enabled or room.configured_control)
        ]
        return {
            "humidity_high": humidity_high,
            "humidity": climate.humidity,
            "humidity_threshold": self.config.dry_humidity_threshold,
            "co2_high": co2_high,
            "co2_ppm": climate.co2_ppm,
            "co2_threshold_ppm": self.config.co2_ventilation_threshold_ppm,
            "thermal_mode_preferred": thermal_mode and (humidity_high or co2_high),
            "dry_recommended": mode_intent.mode == 2,
            "dry_held_reason": "thermal_demand_active" if thermal_mode and humidity_high else None,
            "fan_recommended": mode_intent.mode == 3 and mode_intent.outside_air_intent,
            "fan_held_reason": "thermal_demand_active" if thermal_mode and co2_high else None,
            "dry_zone_ids": active_zone_ids if mode_intent.mode == 2 else [],
            "outside_air_zone_ids": list(self.config.outside_air_zones) if co2_high else [],
        }

    def _adaptive_target(self, ac: dict[str, Any], outside: float, weather: WeatherSignal, climate: ClimateSignal, cooling: bool) -> int:
        target = self._target_setpoint(outside, cooling)
        target = self._forecast_target(
            target,
            _forecast_values_for_control(weather),
            cooling,
            step_minutes=_forecast_step_for_control(weather),
        )
        target = self._humidity_adjusted_target(target, climate.humidity, cooling)
        return _clamp_setpoint(target, ac)

    def _room_demand_target(self, device: AdaptiveDevice, ac: dict[str, Any], cooling: bool) -> int:
        controlled = [
            room
            for room in device.rooms
            if self._participating_room(room) and room.temperature is not None and room.setpoint is not None
        ]
        if controlled:
            setpoints = [float(room.setpoint) for room in controlled if room.setpoint is not None]
            target = min(setpoints) if cooling else max(setpoints)
            return _clamp_setpoint(int(round(target)), ac)
        setpoint = device.setpoint if device.setpoint is not None else _number((ac.get("status") or {}).get("setpoint"))
        if setpoint is None:
            setpoint = self.config.cool_comfort_temp if cooling else self.config.heat_comfort_temp
        return _clamp_setpoint(int(round(setpoint)), ac)

    def _mode_intent(self, device: AdaptiveDevice, ac: dict[str, Any], climate: ClimateSignal) -> AcModeIntent:
        current_mode = device.mode if isinstance(device.mode, int) else _optional_mode((ac.get("status") or {}).get("mode"))
        candidates = [
            room
            for room in device.rooms
            if self._participating_room(room) and room.temperature is not None and room.setpoint is not None
        ]
        if not candidates:
            candidates = [
                room
                for room in device.rooms
                if room.active and room.temperature is not None and room.setpoint is not None
            ]
        outside_air_intent = climate.co2_ppm is not None and climate.co2_ppm >= self.config.co2_ventilation_threshold_ppm
        ventilation_reason = "co2_high" if outside_air_intent else None
        demand = self._thermal_mode_demand(candidates, current_mode)
        if demand is not None:
            mode_name, _score, reason = demand
            mode = 4 if mode_name == "cool" else 1
            return AcModeIntent(
                mode=mode,
                name=_mode_name(mode),
                reason=reason,
                source="zone_temperature",
                current_mode=current_mode,
                outside_air_intent=outside_air_intent,
                ventilation_reason=ventilation_reason,
            )
        if (
            climate.humidity is not None
            and climate.humidity_source == "home_assistant_indoor"
            and climate.humidity >= self.config.dry_humidity_threshold
        ):
            return AcModeIntent(
                mode=2,
                name=_mode_name(2),
                reason="indoor_humidity_extreme",
                source=climate.humidity_source,
                current_mode=current_mode,
                outside_air_intent=outside_air_intent,
                ventilation_reason=ventilation_reason,
            )
        if outside_air_intent:
            return AcModeIntent(
                mode=3,
                name=_mode_name(3),
                reason="co2_high",
                source=climate.co2_source or "co2",
                current_mode=current_mode,
                outside_air_intent=True,
                ventilation_reason=ventilation_reason,
            )
        return AcModeIntent(
            mode=current_mode,
            name=_mode_name(current_mode),
            reason="current_mode_held",
            source="current_mode",
            current_mode=current_mode,
            outside_air_intent=outside_air_intent,
            ventilation_reason=ventilation_reason,
        )

    def _thermal_mode_demand(self, rooms: list[AdaptiveRoom], current_mode: int | None) -> tuple[str, float, str] | None:
        demands: list[tuple[str, float, str]] = []
        for room in rooms:
            if room.temperature is None or room.setpoint is None:
                continue
            temperature = float(room.temperature)
            setpoint = float(room.setpoint)
            if current_mode == 1:
                heat_delta = setpoint - temperature
                cool_delta = temperature - float(self.config.cool_comfort_temp)
                if heat_delta >= 0.5:
                    demands.append(("heat", heat_delta, "room_below_heat_setpoint"))
                elif cool_delta >= 0.5:
                    demands.append(("cool", cool_delta, "room_above_cool_comfort"))
            elif current_mode == 4:
                cool_delta = temperature - setpoint
                heat_delta = float(self.config.heat_comfort_temp) - temperature
                if cool_delta >= 0.5:
                    demands.append(("cool", cool_delta, "room_above_cool_setpoint"))
                elif heat_delta >= 0.5:
                    demands.append(("heat", heat_delta, "room_below_heat_comfort"))
            else:
                cool_delta = temperature - setpoint
                heat_delta = setpoint - temperature
                if cool_delta >= 0.5:
                    demands.append(("cool", cool_delta, "room_above_cool_setpoint"))
                elif heat_delta >= 0.5:
                    demands.append(("heat", heat_delta, "room_below_heat_setpoint"))
        if not demands:
            return None
        return max(demands, key=lambda item: item[1])

    def _participating_room(self, room: AdaptiveRoom) -> bool:
        if room.active and (room.configured_control or room.control_enabled):
            return True
        return self.config.control_strategy in {"zone", "hybrid"} and room.configured_control

    def _control_target(self, device: AdaptiveDevice, ac: dict[str, Any], outside: float, weather: WeatherSignal, climate: ClimateSignal, cooling: bool) -> int:
        if self.config.control_strategy in {"zone", "hybrid"}:
            return self._room_demand_target(device, ac, cooling)
        return self._adaptive_target(ac, outside, weather, climate, cooling)

    def _thermal_intent(
        self,
        device: AdaptiveDevice,
        ac: dict[str, Any],
        outside: float,
        weather: WeatherSignal,
        climate: ClimateSignal,
    ) -> ThermalIntent:
        mode_intent = self._mode_intent(device, ac, climate)
        cooling = True if mode_intent.mode == 4 else False if mode_intent.mode == 1 else None
        setpoint: int | None = None
        setpoint_source: str | None = None
        setpoint_reason: str | None = None
        if cooling is not None:
            setpoint = self._control_target(device, ac, outside, weather, climate, cooling)
            if self.config.control_strategy in {"zone", "hybrid"}:
                setpoint_source = "room_setpoint"
                setpoint_reason = "controlled_zone_demand"
            else:
                setpoint_source = "environment"
                setpoint_reason = "weather_adjusted_global_setpoint"
        return ThermalIntent(
            strategy=self.config.control_strategy,
            mode_intent=mode_intent,
            cooling=cooling,
            setpoint=setpoint,
            setpoint_source=setpoint_source,
            setpoint_reason=setpoint_reason,
        )

    def _mpc_proposal(
        self,
        device: AdaptiveDevice,
        baseline_target: int,
        cooling: bool,
        outside: float,
        weather: WeatherSignal,
        solar: SolarSignal,
        telemetry: AcTelemetrySignal,
        climate: ClimateSignal,
        *,
        advisory: bool = False,
    ):
        if not strategy_uses_mpc(self.config.control_strategy):
            return None
        return self._mpc.propose(
            ac_id=device.ac_id,
            rooms=device.rooms,
            baseline_target=baseline_target,
            cooling=cooling,
            inputs=self._mpc_inputs(outside, weather, solar, telemetry, climate, device=device, cooling=cooling),
            advisory=advisory,
        )

    def _mpc_inputs(
        self,
        outside: float,
        weather: WeatherSignal,
        solar: SolarSignal,
        telemetry: AcTelemetrySignal,
        climate: ClimateSignal,
        *,
        device: AdaptiveDevice | None = None,
        cooling: bool | None = None,
    ) -> MpcInputs:
        airtouch_zone_calls = zone_call_status(device.rooms, cooling) if device is not None else {}
        return MpcInputs(
            horizon_hours=self.config.mpc_horizon_hours,
            outside_temperature=outside,
            outside_forecast=_forecast_values_for_control(weather),
            outside_forecast_step_minutes=_forecast_step_for_control(weather),
            humidity=climate.humidity,
            humidity_assist_threshold=max(0, self.config.dry_humidity_threshold - 10),
            q_solar=solar.q_solar,
            target_policy="room_setpoint" if self.config.control_strategy in {"zone", "hybrid"} else "global_setpoint",
            comfort_weight=self.config.mpc_comfort_weight,
            input_quality={
                "forecast": weather.forecast_quality or {},
                "solar": {
                    "source": solar.source,
                    "error": solar.error,
                    "available": solar.source != "none",
                },
                "humidity": {
                    "source": climate.humidity_source,
                    "available": climate.humidity is not None,
                    "dry_threshold": self.config.dry_humidity_threshold,
                    "assist_threshold": max(0, self.config.dry_humidity_threshold - 10),
                },
                "co2": {
                    "source": climate.co2_source,
                    "available": climate.co2_ppm is not None,
                    "ppm": climate.co2_ppm,
                    "threshold_ppm": self.config.co2_ventilation_threshold_ppm,
                    "outside_air_intent": climate.co2_ppm is not None and climate.co2_ppm >= self.config.co2_ventilation_threshold_ppm,
                },
                "telemetry": _ac_telemetry_status(telemetry),
                "airtouch_zone_calls": airtouch_zone_calls,
            },
        )

    def _target_setpoint(self, outside: float, cooling: bool) -> int:
        outside_round = round(outside)
        if cooling:
            return min(outside_round - self.config.comfort_margin, self.config.cool_comfort_temp)
        return max(outside_round + self.config.comfort_margin, self.config.heat_comfort_temp)

    def _forecast_target(self, current_target: int, forecast_temperatures: tuple[float, ...], cooling: bool, *, step_minutes: float = 60.0) -> int:
        if not forecast_temperatures:
            return current_target
        near_term_count = max(1, int(round((6 * 60) / max(1.0, step_minutes))))
        targets = [self._target_setpoint(temperature, cooling) for temperature in forecast_temperatures[:near_term_count]]
        if cooling:
            return min([current_target, *targets])
        return max([current_target, *targets])

    def _humidity_adjusted_target(self, target: int, humidity: float | None, cooling: bool) -> int:
        if not cooling or humidity is None:
            return target
        high_threshold = self.config.dry_humidity_threshold
        assist_threshold = max(0, high_threshold - 10)
        if humidity >= high_threshold:
            return target - 2
        if humidity >= assist_threshold:
            return target - 1
        return target

    @staticmethod
    def _needs_relax(current: float, target: int, cooling: bool) -> bool:
        return current < target if cooling else current > target

    def _outside_air_status(self, mode_intent: AcModeIntent) -> dict[str, Any]:
        return {
            "intent": mode_intent.outside_air_intent,
            "reason": mode_intent.ventilation_reason,
            "configured_zones": list(self.config.outside_air_zones),
            "commanded_percent": 100 if mode_intent.outside_air_intent and self.config.outside_air_zones else None,
        }

    def _outside_air_action(
        self,
        state: dict[str, Any],
        ac_id: int,
        status: dict[str, Any],
        now: float,
        mode_intent: AcModeIntent,
    ) -> list[TransactionSpec]:
        specs: list[TransactionSpec] = []
        zones = self.config.outside_air_zones
        if mode_intent.outside_air_intent and not zones:
            status["recommendations"].append(f"{_ac_name(ac_id, _indexed(state.get('acs') or {}, ac_id) or {})}: Outside Air Zone Not Configured")
            return specs
        for group_id in zones:
            if mode_intent.outside_air_intent:
                spec = self._set_group_percentage(state, group_id, 100, status, now)
                if spec is not None:
                    specs.append(spec)
                    status["actions"].append(f"{_group_name(group_id, _group_for_id(state, group_id))}: Outside Air Opened")
            else:
                specs.extend(self._restore_group_sensor_control(state, group_id, status, now))
                specs.extend(self._restore_group_percentage(state, group_id, status, now))
        return specs

    def _weather_key(self, ac_id: int) -> str:
        return f"ac:{ac_id}"

    def _weather_suspension(self, ac_id: int) -> dict[str, Any] | None:
        record = self._weather_suspensions.get(self._weather_key(ac_id))
        return record if isinstance(record, dict) else None

    def _record_weather_suspension(self, ac_id: int, opportunity: dict[str, Any], now: float, cooling: bool) -> None:
        window_minutes = _weather_window_minutes(opportunity, cooling)
        self._weather_suspensions[self._weather_key(ac_id)] = {
            "phase": "weather_off",
            "ac": ac_id,
            "turned_off_at": round(now, 3),
            "outside_temperature": opportunity.get("outside_temperature"),
            "setpoint": opportunity.get("setpoint"),
            "mode": opportunity.get("mode"),
            "reason": opportunity.get("reason"),
            "nice_window_minutes": window_minutes,
        }

    def _clear_weather_suspension(self, ac_id: int) -> None:
        self._weather_suspensions.pop(self._weather_key(ac_id), None)

    def _weather_intent_status(
        self,
        ac_id: int,
        opportunity: dict[str, Any],
        suspension: dict[str, Any] | None,
        state: dict[str, Any],
        cooling: bool,
        *,
        cancelled_reason: str | None = None,
        resumed: bool = False,
    ) -> dict[str, Any]:
        window_minutes = _weather_window_minutes(opportunity, cooling)
        intent = "monitor"
        headline = "Weather Holding"
        summary = "Outside Air Is Not Helpful Yet."
        if resumed:
            intent = "resume"
            headline = "AC Resumed"
            summary = "Outside Air No Longer Carries The Load."
        elif cancelled_reason == "no_active_zones":
            intent = "cancelled"
            headline = "Resume Cancelled"
            summary = "No Zones Are On."
        elif cancelled_reason == "ac_power_changed_externally":
            intent = "cancelled"
            headline = "Resume Cancelled"
            summary = "AC Power Changed Externally."
        elif suspension is not None:
            intent = "paused"
            headline = "AC Paused"
            summary = "Outside Air Can Carry The Load."
        elif opportunity.get("recommend_off"):
            intent = "pause_recommended" if self.config.mode == "recommend" else "pause"
            headline = "Nice Outside"
            summary = "Outside Air Can Carry The Load."
        elif opportunity.get("outside_favourable"):
            intent = "hold"
            headline = "Outside Air Can Help"
            summary = "Waiting For Forecast Or Indoor Comfort."
        return {
            "ac": ac_id,
            "intent": intent,
            "headline": headline,
            "summary": summary,
            "reason": cancelled_reason or opportunity.get("reason"),
            "outside_temperature": opportunity.get("outside_temperature"),
            "setpoint": opportunity.get("setpoint"),
            "nice_outside": bool(opportunity.get("outside_favourable")),
            "open_windows": bool(opportunity.get("open_windows_intent")),
            "pause_recommended": bool(opportunity.get("recommend_off")),
            "pause_active": suspension is not None,
            "resume_pending": suspension is not None and not opportunity.get("recommend_off"),
            "resume_cancelled": cancelled_reason is not None,
            "nice_window_minutes": window_minutes,
            "suspension_active": suspension is not None,
            "cancelled_reason": cancelled_reason,
            "active_zones_available": _has_active_zone_for_ac(
                state,
                ac_id,
                _indexed(state.get("acs") or {}, ac_id) or {},
            ),
        }

    def _empty_status(self) -> dict[str, Any]:
        return {
            "mode": self.config.mode,
            "config": self.public_config(),
            "outside_temperature": None,
            "recommendations": [],
            "actions": [],
            "command_intents": [],
            "intents": [],
            "errors": [],
            "evaluations": [],
            "forecast_temperatures": [],
            "forecast_quality": {"status": "missing", "used_for_control": False},
            "solar": {"q_solar": 0.0, "source": "none", "irradiance_w_m2": None, "cloud_cover": None, "sun_elevation": None},
            "learning": self._mpc.status(time.monotonic()),
            "restore_state": self.export_restore_state(),
            "weather_state": self.export_weather_state(),
            "active_restore": sorted(self._restore_records),
            "active_ac": active_ac_restore_ids(self._restore_records),
            "active_groups": active_group_restore_ids(self._restore_records, "setpoint"),
            "active_dampers": sorted(set(active_group_restore_ids(self._restore_records, "percentage")) | set(active_group_restore_ids(self._restore_records, "sensor_control"))),
        }

    def _final_status(self, status: dict[str, Any]) -> dict[str, Any]:
        status["restore_state"] = self.export_restore_state()
        status["weather_state"] = self.export_weather_state()
        status["active_restore"] = sorted(self._restore_records)
        status["active_ac"] = active_ac_restore_ids(self._restore_records)
        status["active_groups"] = active_group_restore_ids(self._restore_records, "setpoint")
        status["active_dampers"] = sorted(set(active_group_restore_ids(self._restore_records, "percentage")) | set(active_group_restore_ids(self._restore_records, "sensor_control")))
        status["outside_air_zones"] = list(self.config.outside_air_zones)
        status["learning"] = self._mpc.status(time.monotonic())
        status["intents"] = [_intent_status(evaluation, status) for evaluation in status.get("evaluations", [])]
        for evaluation, intent in zip(status.get("evaluations", []), status["intents"], strict=False):
            evaluation["intent"] = intent
        status["ui"] = build_adaptive_ui_contract(status)
        return status
