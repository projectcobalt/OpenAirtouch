"""Resolve the synthetic OpenAirTouch touchpad temperature."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TouchpadTemperatureResult:
    temperature: float
    source: str
    detail: dict[str, Any] = field(default_factory=dict)


def resolve_touchpad_temperature(
    runtime_snapshot: dict[str, Any] | None,
    integrations: dict[str, Any] | None,
    adaptive_status: dict[str, Any] | None,
    *,
    fallback: float = 23.0,
) -> TouchpadTemperatureResult:
    """Resolve the heartbeat temperature using the app-wide source priority."""

    adaptive = _adaptive_temperature(adaptive_status)
    if adaptive is not None:
        return adaptive

    indoor_state = ((integrations or {}).get("indoor") or {}).get("state") or {}
    indoor = _number(indoor_state.get("temperature") if isinstance(indoor_state, dict) else None)
    if indoor is not None:
        return TouchpadTemperatureResult(round(indoor, 1), "home_assistant_indoor", {"field": "temperature"})

    state = ((runtime_snapshot or {}).get("state") or {}) if runtime_snapshot else {}
    on_zones = _zone_temperatures(state, require_on=True)
    if on_zones:
        return TouchpadTemperatureResult(_average(on_zones), "on_zone_average", {"count": len(on_zones)})

    all_zones = _zone_temperatures(state, require_on=False)
    if all_zones:
        return TouchpadTemperatureResult(_average(all_zones), "zone_average", {"count": len(all_zones)})

    configured = _number(fallback)
    return TouchpadTemperatureResult(round(configured if configured is not None else 23.0, 1), "fallback", {})


def _adaptive_temperature(adaptive_status: dict[str, Any] | None) -> TouchpadTemperatureResult | None:
    if not isinstance(adaptive_status, dict):
        return None
    if adaptive_status.get("mode") != "adaptive":
        return None
    runtime_control = adaptive_status.get("runtime_control") or {}
    if runtime_control.get("connected") is not True:
        return None
    config = adaptive_status.get("config") or {}
    if config.get("control_strategy") != "hybrid":
        return None
    for evaluation in reversed(adaptive_status.get("evaluations") or []):
        if not isinstance(evaluation, dict):
            continue
        hybrid = evaluation.get("hybrid") or {}
        temperature = _number(hybrid.get("control_temperature"))
        if temperature is None:
            temperature = _number(hybrid.get("touchpad_temperature"))
        if temperature is not None:
            return TouchpadTemperatureResult(
                round(temperature, 1),
                "adaptive_control",
                {
                    "ac": evaluation.get("ac"),
                    "strategy": hybrid.get("strategy") or "hybrid",
                    "field": "control_temperature",
                },
            )
    return None


def _zone_temperatures(state: dict[str, Any], *, require_on: bool) -> list[float]:
    groups = state.get("active_groups") or state.get("groups") or {}
    if not isinstance(groups, dict):
        return []
    values: list[float] = []
    for group in groups.values():
        if not isinstance(group, dict):
            continue
        status = group.get("status") or {}
        if require_on and not _zone_is_on(status):
            continue
        temperature = _number(status.get("temperature"))
        if temperature is not None:
            values.append(temperature)
    return values


def _zone_is_on(status: dict[str, Any]) -> bool:
    power_name = str(status.get("power_name") or "").strip().lower()
    if power_name in {"on", "turbo"}:
        return True
    if power_name in {"off", "none"}:
        return False
    power = status.get("power")
    if isinstance(power, bool):
        return power
    power_code = _number(power)
    return power_code is not None and power_code > 0


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 1)


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None
