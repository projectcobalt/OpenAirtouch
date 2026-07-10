"""Adaptive control runtime evaluator."""

from __future__ import annotations

import time
from typing import Any

from ..session.queue import TransactionSpec
from .adaptive_airtouch import translate_airtouch_snapshot
from .adaptive_contracts import build_adaptive_input_contract
from .adaptive_intent import _mode_intent_status, _thermal_intent_status
from .adaptive_runtime_state import _ac_name, _indexed, _iter_acs, _optional_int
from .adaptive_signals import (
    _ac_telemetry_signal,
    _ac_telemetry_status,
    _climate_for_ac,
    _solar_signal,
    _weather_signal,
)


class AdaptiveEvaluatorMixin:
    def evaluate(self, runtime_snapshot: dict[str, Any] | None, integrations: dict[str, Any], *, now: float | None = None) -> list[TransactionSpec]:
        now = time.monotonic() if now is None else now
        status = self._empty_status()
        status["config"] = self.public_config()
        if runtime_snapshot is None:
            status["note"] = "Runtime state is not available"
            self._status = self._final_status(status)
            return []
        runtime_control = runtime_control_status(runtime_snapshot)
        status["runtime_control"] = runtime_control
        if not runtime_control["connected"]:
            status["note"] = runtime_control["reason"]
            self._status = self._final_status(status)
            return []
        if now < self._next_check:
            return []
        self._next_check = now + max(5.0, self.config.check_interval)
        inputs = build_adaptive_input_contract(runtime_snapshot, integrations, runtime_control)
        weather = inputs.weather
        indoor = inputs.indoor
        weather_signal = _weather_signal(weather, integrations, horizon_hours=self.config.mpc_horizon_hours)
        solar_signal = _solar_signal(weather, integrations)
        telemetry_signal = _ac_telemetry_signal(integrations)
        state = inputs.airtouch_state
        self._set_compressor_groups(compressor_groups_from_zone_map(state) or self.config.compressor_groups)
        mode = self.config.mode
        adaptive_snapshot = translate_airtouch_snapshot(
            state,
            control_zones=self.config.control_zones,
            control_active=mode == "adaptive",
        )
        self._mpc.observe(
            adaptive_snapshot,
            now=now,
            outside_temperature=weather_signal.outside_temperature,
            q_solar=solar_signal.q_solar,
        )
        outside = weather_signal.outside_temperature
        status["outside_temperature"] = outside
        status["forecast_temperatures"] = list(weather_signal.forecast_temperatures)
        status["forecast_quality"] = weather_signal.forecast_quality or {}
        status["solar"] = {
            "q_solar": solar_signal.q_solar,
            "source": solar_signal.source,
            "irradiance_w_m2": solar_signal.irradiance_w_m2,
            "cloud_cover": solar_signal.cloud_cover,
            "sun_elevation": solar_signal.sun_elevation,
        }
        if solar_signal.error is not None:
            status["errors"].append(f"Solar: {solar_signal.error}")
        status["ac_telemetry"] = _ac_telemetry_status(telemetry_signal)
        if telemetry_signal.error is not None:
            status["errors"].append(f"AC telemetry: {telemetry_signal.error}")
        status["zone_names"] = _zone_names_from_state(state)
        if outside is None:
            status["note"] = "Outside temperature is not available"
            specs = self._restore_all(state, status, now) if self.config.mode != "off" else []
            self._status = self._final_status(status)
            return specs
        if mode == "off":
            specs = self._restore_all(state, status, now)
            self._status = self._final_status(status)
            return specs
        specs: list[TransactionSpec] = []
        planned_power_off: set[int] = set()
        for device in adaptive_snapshot.devices:
            ac_id = device.ac_id
            ac = _indexed(state.get("acs") or {}, ac_id) or {}
            has_weather_suspension = self.config.control_strategy == "weather" and self._weather_suspension(ac_id) is not None
            adaptive_can_prepare = (
                mode == "adaptive"
                and self.config.control_strategy in {"zone", "hybrid"}
                and not device.power_on
                and device.mode is not None
            )
            if (not device.power_on and not adaptive_can_prepare) or device.mode is None:
                if mode == "adaptive" and has_weather_suspension:
                    climate = _climate_for_ac(state, ac_id, ac, indoor, weather_signal)
                    thermal_intent = self._thermal_intent(device, ac, outside, weather_signal, climate)
                    mode_intent = thermal_intent.mode_intent
                    status["evaluations"].append({
                        "ac": ac_id,
                        "name": _ac_name(ac_id, ac),
                        "indoor_temperature": climate.indoor_temperature,
                        "indoor_source": climate.indoor_source,
                        "humidity": climate.humidity,
                        "humidity_source": climate.humidity_source,
                        "co2_ppm": climate.co2_ppm,
                        "co2_source": climate.co2_source,
                        "mode_intent": _mode_intent_status(mode_intent),
                        "thermal_intent": _thermal_intent_status(thermal_intent),
                    })
                    specs.extend(self._weather_action(state, ac_id, ac, outside, weather_signal, climate, thermal_intent, status, now, planned_power_off))
                else:
                    specs.extend(self._restore_ac(state, ac_id, status, now))
                continue
            climate = _climate_for_ac(state, ac_id, ac, indoor, weather_signal)
            thermal_intent = self._thermal_intent(device, ac, outside, weather_signal, climate)
            mode_intent = thermal_intent.mode_intent
            status["evaluations"].append({
                "ac": ac_id,
                "name": _ac_name(ac_id, ac),
                "indoor_temperature": climate.indoor_temperature,
                "indoor_source": climate.indoor_source,
                "humidity": climate.humidity,
                "humidity_source": climate.humidity_source,
                "co2_ppm": climate.co2_ppm,
                "co2_source": climate.co2_source,
                "mode_intent": _mode_intent_status(mode_intent),
                "thermal_intent": _thermal_intent_status(thermal_intent),
            })
            if mode == "recommend":
                self._recommend_action(device, ac, outside, weather_signal, solar_signal, telemetry_signal, climate, thermal_intent, status)
            elif mode == "adaptive":
                if self.config.control_strategy == "weather":
                    specs.extend(self._weather_action(state, ac_id, ac, outside, weather_signal, climate, thermal_intent, status, now, planned_power_off))
                elif self.config.control_strategy == "hybrid":
                    specs.extend(self._hybrid_damper_action(state, device, ac, outside, weather_signal, solar_signal, telemetry_signal, climate, thermal_intent, status, now))
                else:
                    specs.extend(self._adaptive_action(state, device, ac, outside, weather_signal, solar_signal, telemetry_signal, climate, thermal_intent, status, now))
        self._status = self._final_status(status)
        return specs


def runtime_control_status(runtime_snapshot: dict[str, Any]) -> dict[str, Any]:
    runtime = runtime_snapshot.get("runtime")
    if not isinstance(runtime, dict):
        return {"connected": False, "reason": "Runtime Connection State Is Not Available"}
    connected = runtime.get("connected") is True
    return {
        "connected": connected,
        "reason": None if connected else "Runtime Is Not Connected To The Mainboard",
    }


def _zone_names_from_state(state: dict[str, Any]) -> dict[str, str]:
    groups = state.get("groups") or state.get("active_groups") or {}
    if not isinstance(groups, dict):
        return {}
    names: dict[str, str] = {}
    for key, group in groups.items():
        group_id = _optional_int(key)
        if group_id is None or not isinstance(group, dict):
            continue
        name = group.get("name") or (group.get("name_record") or {}).get("name")
        if isinstance(name, str) and name.strip():
            names[str(group_id)] = name.strip()
    return names


def compressor_groups_from_zone_map(state: dict[str, Any]) -> tuple[tuple[int, ...], ...]:
    zones_by_ac: dict[int, set[int]] = {}
    for ac_id, ac in _iter_acs(state):
        base = ac.get("base") or {}
        start = base.get("group_start")
        count = base.get("group_count")
        if not isinstance(start, int) or not isinstance(count, int) or count <= 0:
            continue
        zones_by_ac[ac_id] = set(range(start, start + count))
    if len(zones_by_ac) < 2:
        return ()

    parent = {ac_id: ac_id for ac_id in zones_by_ac}

    def find(ac_id: int) -> int:
        while parent[ac_id] != ac_id:
            parent[ac_id] = parent[parent[ac_id]]
            ac_id = parent[ac_id]
        return ac_id

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    entries = sorted(zones_by_ac.items())
    for index, (left_id, left_zones) in enumerate(entries):
        for right_id, right_zones in entries[index + 1:]:
            if left_zones.intersection(right_zones):
                union(left_id, right_id)

    groups: dict[int, list[int]] = {}
    for ac_id in zones_by_ac:
        groups.setdefault(find(ac_id), []).append(ac_id)
    return tuple(tuple(sorted(members)) for members in groups.values() if len(members) >= 2)
