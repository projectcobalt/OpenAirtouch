"""AirTouch zone call-state helpers for adaptive control."""

from __future__ import annotations

from typing import Any, Iterable


def zone_call_status(rooms: Iterable[Any], cooling: bool | None) -> dict[str, dict[str, Any]]:
    """Classify configured zones against AirTouch's whole-degree call threshold."""

    result: dict[str, dict[str, Any]] = {}
    mode = "cool" if cooling is True else "heat" if cooling is False else None
    for room in rooms:
        if not getattr(room, "configured_control", False):
            continue
        room_id = str(int(getattr(room, "id")))
        temperature = getattr(room, "temperature", None)
        setpoint = getattr(room, "setpoint", None)
        active = bool(getattr(room, "active", False))
        entry: dict[str, Any] = {
            "state": "unknown",
            "mode": mode,
            "temperature": temperature,
            "control_temperature": _control_temperature(temperature),
            "setpoint": setpoint,
            "active": active,
            "reason": "missing_mode_or_temperature",
        }
        if not active:
            entry["state"] = "participating_off"
            entry["reason"] = "zone_is_off"
        elif cooling is None or temperature is None or setpoint is None:
            entry["state"] = "unknown"
            entry["reason"] = "missing_mode_or_temperature"
        else:
            entry.update(_thermal_call_state(float(temperature), int(round(float(setpoint))), bool(cooling)))
        result[room_id] = entry
    return result


def _thermal_call_state(temperature: float, setpoint: int, cooling: bool) -> dict[str, Any]:
    control_temperature = _control_temperature(temperature)
    if control_temperature is None:
        return {"state": "unknown", "reason": "missing_temperature"}
    if cooling:
        if control_temperature > setpoint:
            return {"state": "calling", "reason": "control_temperature_above_cool_setpoint"}
        if temperature > setpoint:
            return {"state": "waiting_for_call_threshold", "reason": "control_temperature_not_above_cool_setpoint"}
        return {"state": "satisfied_idle", "reason": "temperature_at_or_below_cool_setpoint"}
    if control_temperature < setpoint:
        return {"state": "calling", "reason": "control_temperature_below_heat_setpoint"}
    if temperature < setpoint:
        return {"state": "waiting_for_call_threshold", "reason": "control_temperature_not_below_heat_setpoint"}
    return {"state": "satisfied_idle", "reason": "temperature_at_or_above_heat_setpoint"}


def _control_temperature(temperature: Any) -> int | None:
    try:
        return int(round(float(temperature)))
    except (TypeError, ValueError):
        return None
