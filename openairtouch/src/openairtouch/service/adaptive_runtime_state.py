"""Shared OpenAirTouch adaptive helpers for reading runtime state."""

from __future__ import annotations

from typing import Any


def _clamp_setpoint(target: int, ac: dict[str, Any]) -> int:
    settings = ac.get("settings") or {}
    minimum = _number(settings.get("min_setpoint"))
    maximum = _number(settings.get("max_setpoint"))
    if minimum is not None:
        target = max(target, int(minimum))
    if maximum is not None:
        target = min(target, int(maximum))
    return target


def _iter_acs(state: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    result = []
    for key, value in (state.get("acs") or {}).items():
        ac_id = _optional_int(key)
        if ac_id is not None and isinstance(value, dict):
            result.append((ac_id, value))
    return sorted(result)


def _groups_for_ac(state: dict[str, Any], ac_id: int, ac: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    base = ac.get("base") or {}
    groups = state.get("active_groups") or state.get("groups") or {}
    start = base.get("group_start")
    count = base.get("group_count")
    result = []
    for key, value in groups.items():
        group_id = _optional_int(key)
        if group_id is None or not isinstance(value, dict):
            continue
        if isinstance(start, int) and isinstance(count, int) and not (start <= group_id < start + count):
            continue
        result.append((group_id, value))
    return sorted(result)


def _has_active_zone_for_ac(state: dict[str, Any], ac_id: int, ac: dict[str, Any]) -> bool:
    return any(
        (group.get("status") or {}).get("power_name") in {"on", "turbo"}
        for _group_id, group in _groups_for_ac(state, ac_id, ac)
    )


def _group_for_id(state: dict[str, Any], group_id: int) -> dict[str, Any]:
    group = _indexed(state.get("active_groups") or {}, group_id)
    if isinstance(group, dict):
        return group
    group = _indexed(state.get("groups") or {}, group_id)
    return group if isinstance(group, dict) else {}


def _ac_setting_record_for(state: dict[str, Any], ac_id: int | None) -> dict[str, Any] | None:
    if ac_id is None:
        return None
    ac = _indexed(state.get("acs") or {}, ac_id)
    if not isinstance(ac, dict):
        return None
    settings = ac.get("settings") or {}
    if not isinstance(settings, dict):
        return None
    return {
        "ac": ac_id,
        "hide_spill_group": bool(settings.get("hide_spill_group", False)),
        "ctrl_thermostat": int(settings.get("ctrl_thermostat", 0) or 0),
        "cool_adjust": int(settings.get("cool_adjust", 0) or 0),
        "heat_adjust": int(settings.get("heat_adjust", 0) or 0),
        "modes": dict(settings.get("modes") or {}),
        "fan_values": dict(settings.get("fan_values") or {}),
        "auto_off": bool(settings.get("auto_off", False)),
        "on_time_limit": int(settings.get("on_time_limit", 0) or 0),
        "max_setpoint": int(settings.get("max_setpoint", 30) or 30),
        "min_setpoint": int(settings.get("min_setpoint", 16) or 16),
        "selector_visibility": dict(settings.get("selector_visibility") or {}),
    }


def _ac_setting_records_from_state(state: dict[str, Any]) -> list[dict[str, Any]]:
    acs = state.get("acs") or {}
    if not isinstance(acs, dict):
        return []
    records: list[dict[str, Any]] = []
    for key in sorted(acs, key=lambda value: _optional_int(value) if _optional_int(value) is not None else 999):
        ac_id = _optional_int(key)
        record = _ac_setting_record_for(state, ac_id)
        if record is not None:
            records.append(record)
    return records


def _indexed(mapping: Any, key: int | None) -> Any:
    if key is None:
        return None
    if isinstance(mapping, dict):
        return mapping.get(key) if key in mapping else mapping.get(str(key))
    if isinstance(mapping, list) and 0 <= key < len(mapping):
        return mapping[key]
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_mode(value: Any) -> int | None:
    mode = _optional_int(value)
    return mode if mode in {0, 1, 2, 3, 4} else None


def _mode_name(mode: int | None) -> str:
    return {
        0: "Auto",
        1: "Heat",
        2: "Dry",
        3: "Fan",
        4: "Cool",
    }.get(mode, "Unknown")


def _cooling_for_mode(mode: int | None, *, default: bool) -> bool:
    if mode == 1:
        return False
    if mode == 4:
        return True
    return default


def _command_value(payload: dict[str, Any]) -> int | bool | None:
    for key in ("mode", "setpoint", "percentage", "temperature", "ctrl_thermostat", "power_on", "on"):
        if key in payload:
            value = payload[key]
            if isinstance(value, bool):
                return value
            return _optional_int(value)
    return None


def _ac_name(ac_id: int, ac: dict[str, Any]) -> str:
    base = ac.get("base") or {}
    return str(base.get("name") or f"AC {ac_id + 1}")


def _group_name(group_id: int, group: dict[str, Any]) -> str:
    base = group.get("base") or {}
    return str(group.get("name") or base.get("name") or f"Zone {group_id + 1}")
