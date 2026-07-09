"""Adaptive control state import/export helpers."""

from __future__ import annotations

from typing import Any

from .adaptive_runtime_state import _optional_int


def export_restore_state(records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"records": dict(records)}


def import_restore_records(payload: Any) -> dict[str, dict[str, Any]] | None:
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, dict):
        return None
    return {
        str(key): dict(value)
        for key, value in records.items()
        if isinstance(value, dict) and isinstance(value.get("action"), str)
    }


def export_weather_state(suspensions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"suspensions": dict(suspensions)}


def import_weather_suspensions(payload: Any) -> dict[str, dict[str, Any]] | None:
    suspensions = payload.get("suspensions") if isinstance(payload, dict) else None
    if not isinstance(suspensions, dict):
        return None
    return {
        str(key): dict(value)
        for key, value in suspensions.items()
        if isinstance(value, dict) and value.get("phase") == "weather_off"
    }


def active_ac_restore_ids(records: dict[str, dict[str, Any]]) -> list[int]:
    ids: set[int] = set()
    for key in records:
        parts = key.split(":")
        if len(parts) >= 3 and parts[0] == "ac":
            value = _optional_int(parts[1])
            if value is not None:
                ids.add(value)
    return sorted(ids)


def active_group_restore_ids(records: dict[str, dict[str, Any]], surface: str) -> list[int]:
    ids: set[int] = set()
    for key in records:
        parts = key.split(":")
        if len(parts) >= 3 and parts[0] == "group" and parts[2] == surface:
            value = _optional_int(parts[1])
            if value is not None:
                ids.add(value)
    return sorted(ids)
