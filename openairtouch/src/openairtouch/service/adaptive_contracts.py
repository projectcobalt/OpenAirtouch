"""Stable adaptive-layer contracts for UI and protocol boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

AdaptiveAuthority = Literal["off", "insight", "control"]
AdaptiveCommandSurface = Literal["ac", "zone", "outside_air", "restore", "touchpad"]


@dataclass(frozen=True)
class AdaptiveCommandIntent:
    """Protocol-neutral command request emitted by adaptive control."""

    action: str
    data: dict[str, Any]
    surface: AdaptiveCommandSurface
    reason: str
    restore_key: str | None = None
    expected_value: int | bool | None = None

    def as_transaction_request(self) -> dict[str, Any]:
        return {"action": self.action, "data": dict(self.data)}

    def as_status(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "data": dict(self.data),
            "surface": self.surface,
            "reason": self.reason,
            "restore_key": self.restore_key,
            "expected_value": self.expected_value,
        }


@dataclass(frozen=True)
class AdaptiveInputContract:
    """Normalized input bundle consumed by adaptive control."""

    runtime_connected: bool
    runtime_reason: str | None
    airtouch_state: dict[str, Any]
    weather: dict[str, Any] = field(default_factory=dict)
    indoor: dict[str, Any] = field(default_factory=dict)
    forecast: dict[str, Any] = field(default_factory=dict)
    solar: dict[str, Any] = field(default_factory=dict)
    ac_telemetry: dict[str, Any] = field(default_factory=dict)


def build_adaptive_input_contract(
    runtime_snapshot: dict[str, Any],
    integrations: dict[str, Any] | None,
    runtime_control: dict[str, Any],
) -> AdaptiveInputContract:
    """Normalize runtime and integration data before strategy evaluation."""

    integrations = integrations if isinstance(integrations, dict) else {}
    return AdaptiveInputContract(
        runtime_connected=runtime_control.get("connected") is True,
        runtime_reason=runtime_control.get("reason") if isinstance(runtime_control.get("reason"), str) else None,
        airtouch_state=_dict(runtime_snapshot.get("state")),
        weather=_integration_state(integrations, "weather"),
        indoor=_integration_state(integrations, "indoor"),
        forecast=_integration_state(integrations, "forecast"),
        solar=_integration_state(integrations, "solar"),
        ac_telemetry=_integration_state(integrations, "ac_telemetry"),
    )


def build_adaptive_ui_contract(status: dict[str, Any]) -> dict[str, Any]:
    """Build the UI-facing adaptive status contract from rich backend status."""

    config = status.get("config") if isinstance(status.get("config"), dict) else {}
    mode = str(status.get("mode") or config.get("mode") or "off")
    strategy = str(config.get("control_strategy") or "weather")
    intent = _first_dict(status.get("intents"))
    evaluation = _evaluation_for_intent(status.get("evaluations"), intent)
    summary = _summary(status, intent, mode, strategy)
    surfaces = {
        "environment": _environment_surface(status, evaluation),
        "zone": _zone_surface(status, evaluation, intent),
        "hybrid": _hybrid_surface(evaluation, strategy),
    }
    plan = _plan(evaluation, intent)
    inputs = _inputs(status, evaluation)
    commands = _commands(status, intent)
    analytics = _analytics(status, commands)
    return {
        "version": 1,
        "summary": summary,
        "surfaces": surfaces,
        "metrics": _metrics(summary, surfaces, plan, inputs, commands),
        "analytics": analytics,
        "plan": plan,
        "inputs": inputs,
        "commands": commands,
    }


def _summary(status: dict[str, Any], intent: dict[str, Any], mode: str, strategy: str) -> dict[str, Any]:
    note = status.get("note")
    headline = str(note or intent.get("headline") or ("Adaptive Control Is Off" if mode == "off" else "Adaptive Ready"))
    detail = str(intent.get("summary") or note or _first_text(status.get("recommendations")) or "No adaptive recommendation is active.")
    authority = str(intent.get("authority") or ("off" if mode == "off" else "insight" if mode == "recommend" else "control"))
    return {
        "headline": headline,
        "detail": detail,
        "authority": authority,
        "mode": mode,
        "strategy": strategy,
        "intent": intent.get("intent") or ("off" if mode == "off" else "monitor"),
        "reason": intent.get("reason") or status.get("note"),
        "confidence": intent.get("confidence"),
    }


def _environment_surface(status: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    weather = _dict(evaluation.get("weather_intent"))
    opportunity = _dict(evaluation.get("weather_opportunity"))
    air_quality = _dict(evaluation.get("air_quality"))
    outside = _first_number(weather.get("outside_temperature"), opportunity.get("outside_temperature"), status.get("outside_temperature"))
    forecast = _dict(status.get("forecast_quality"))
    headline = str(weather.get("headline") or ("Outside Air Recommended" if air_quality.get("fan_recommended") else "Environment Watching"))
    detail = str(weather.get("summary") or weather.get("reason") or opportunity.get("reason") or "Weather and air-quality inputs are being watched.")
    return {
        "headline": headline,
        "detail": detail,
        "state": weather.get("intent") or "monitor",
        "fields": [
            _temperature_field("Outside", outside),
            _text_field("Forecast", _title(forecast.get("status") or "missing"), raw=forecast.get("status")),
            _text_field("Pause", _pause_state(weather), raw=weather.get("intent")),
            _text_field("Fresh Air", "Recommended" if weather.get("outside_air_intent") or air_quality.get("fan_recommended") else "Not Requested"),
        ],
    }


def _zone_surface(status: dict[str, Any], evaluation: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    mpc = _dict(evaluation.get("mpc"))
    learning = _dict(status.get("learning"))
    zones = _dict(learning.get("zones"))
    ready = sum(1 for zone in zones.values() if isinstance(zone, dict) and zone.get("mpc_ready") is True)
    learning_count = sum(1 for zone in zones.values() if isinstance(zone, dict) and zone.get("learn") is True)
    target = _first_number(intent.get("recommended_target"), mpc.get("target"), evaluation.get("target"))
    runtime = _first_number(intent.get("runtime_hours"), _dict(mpc.get("runtime_forecast")).get("runtime_hours"), mpc.get("projected_runtime_hours"))
    headline = str(intent.get("headline") or ("Zone Models Ready" if ready else "Waiting For Zones"))
    detail = str(intent.get("summary") or mpc.get("reason") or _first_text(status.get("recommendations")) or "Zone model status is available.")
    return {
        "headline": headline,
        "detail": detail,
        "state": intent.get("intent") or "monitor",
        "fields": [
            _temperature_field("Target", target),
            _hours_field("Expected Runtime", runtime),
            _text_field("Learning", f"{ready} ready / {learning_count} learning", raw={"ready": ready, "learning": learning_count}),
            _text_field("Action", _title(mpc.get("action") or intent.get("intent") or "monitor"), raw=mpc.get("action") or intent.get("intent")),
        ],
    }


def _hybrid_surface(evaluation: dict[str, Any], strategy: str) -> dict[str, Any]:
    hybrid = _dict(evaluation.get("hybrid"))
    mpc = _dict(evaluation.get("mpc"))
    dampers = _dict(hybrid.get("damper_percentages"))
    control_temperature = _first_number(hybrid.get("control_temperature"), _first_series_value(mpc, "control_temperature"))
    headline = "Damper Plan" if strategy == "hybrid" else "Hybrid Standby"
    if hybrid.get("touchpad_temperature_note"):
        detail = str(hybrid.get("touchpad_temperature_note"))
    elif dampers:
        detail = _damper_text(dampers)
    else:
        detail = "No hybrid damper plan is active."
    return {
        "headline": headline,
        "detail": detail,
        "state": "planned" if dampers else "idle",
        "fields": [
            _temperature_field("Control Temperature", control_temperature),
            _text_field("Zone Airflow", _damper_text(dampers) if dampers else "-", raw=dampers),
            _text_field("Touchpad Sensor", _touchpad_sensor_text(hybrid), raw=hybrid.get("touchpad_sensor")),
            _text_field("Strategy", _title(strategy), raw=strategy),
        ],
    }


def _plan(evaluation: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    mpc = _dict(evaluation.get("mpc"))
    hybrid = _dict(evaluation.get("hybrid"))
    runtime = _dict(mpc.get("runtime_forecast"))
    return {
        "target": _first_number(intent.get("recommended_target"), mpc.get("target"), evaluation.get("target")),
        "runtime_hours": _first_number(intent.get("runtime_hours"), runtime.get("runtime_hours"), mpc.get("projected_runtime_hours")),
        "action": mpc.get("action") or intent.get("intent"),
        "control_temperature": _first_number(hybrid.get("control_temperature"), _first_series_value(mpc, "control_temperature")),
        "average_indoor_temperature": _first_number(evaluation.get("indoor_temperature"), _first_series_value(mpc, "average_indoor_temperature")),
        "damper_percentages": _dict(hybrid.get("damper_percentages")),
        "zone_power_fractions": _dict(mpc.get("zone_power_fractions")),
        "action_windows": list(runtime.get("action_windows") or []),
        "series": list(runtime.get("series") or []),
    }


def _inputs(status: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    learning = _dict(status.get("learning"))
    return {
        "outside_temperature": status.get("outside_temperature"),
        "forecast_quality": _dict(status.get("forecast_quality")),
        "indoor_temperature": evaluation.get("indoor_temperature"),
        "indoor_source": evaluation.get("indoor_source"),
        "humidity": evaluation.get("humidity"),
        "humidity_source": evaluation.get("humidity_source"),
        "co2_ppm": evaluation.get("co2_ppm"),
        "co2_source": evaluation.get("co2_source"),
        "solar": _dict(status.get("solar")),
        "ac_telemetry": _dict(status.get("ac_telemetry")),
        "learning_paused_reason": learning.get("learning_paused_reason"),
        "errors": list(status.get("errors") or []),
    }


def _commands(status: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": status.get("mode"),
        "authority": intent.get("authority"),
        "recommendations": list(status.get("recommendations") or []),
        "actions": list(status.get("actions") or []),
        "active_restore": list(status.get("active_restore") or []),
        "active_ac": list(status.get("active_ac") or []),
        "active_groups": list(status.get("active_groups") or []),
        "active_dampers": list(status.get("active_dampers") or []),
        "command_intents": list(status.get("command_intents") or []),
    }


def _metrics(
    summary: dict[str, Any],
    surfaces: dict[str, Any],
    plan: dict[str, Any],
    inputs: dict[str, Any],
    commands: dict[str, Any],
) -> list[dict[str, Any]]:
    learning_reason = inputs.get("learning_paused_reason")
    learning_field = _field_by_label(_dict(surfaces.get("zone")), "Learning")
    active_control_count = (
        _count(commands.get("active_groups"))
        + _count(commands.get("active_dampers"))
        + _count(commands.get("active_ac"))
        + _count(commands.get("active_restore"))
    )
    return [
        _text_field("Authority", _title(summary.get("authority")), raw=summary.get("authority")),
        _text_field("Learning", _title(learning_reason) if learning_reason else learning_field.get("value", "-"), raw=learning_reason or learning_field.get("raw")),
        _temperature_field("Control Temperature", plan.get("control_temperature")),
        _text_field("Control", f"{active_control_count} active changes" if active_control_count else "Idle", raw=active_control_count),
        _text_field("Ownership", summary.get("detail") or summary.get("reason") or "-", raw=summary.get("reason")),
    ]


def _analytics(status: dict[str, Any], commands: dict[str, Any]) -> dict[str, Any]:
    learning = _dict(status.get("learning"))
    zones = _dict(learning.get("zones"))
    history_by_zone = _dict(learning.get("analytics"))
    forecasts_by_zone = _dict(learning.get("forecasts"))
    active_groups = _id_set(commands.get("active_groups"))
    active_dampers = _id_set(commands.get("active_dampers"))
    zone_ids = _sorted_ids(set(zones) | set(history_by_zone) | set(forecasts_by_zone) | active_groups | active_dampers)
    return {
        "zones": [
            _analytics_zone(
                zone_id,
                _dict(zones.get(str(zone_id), zones.get(zone_id))),
                _list(history_by_zone.get(str(zone_id), history_by_zone.get(zone_id))),
                _list(forecasts_by_zone.get(str(zone_id), forecasts_by_zone.get(zone_id))),
                active_groups,
                active_dampers,
            )
            for zone_id in zone_ids
        ]
    }


def _analytics_zone(
    zone_id: int,
    zone: dict[str, Any],
    history: list[Any],
    forecast: list[Any],
    active_groups: set[int],
    active_dampers: set[int],
) -> dict[str, Any]:
    flags: list[str] = []
    if zone_id in active_groups:
        flags.append("Control")
    if zone_id in active_dampers:
        flags.append("Damper")
    if zone.get("mpc_ready") is True:
        flags.append("Ready")
    if zone.get("learn") is True:
        flags.append("Learning")
    label = _sparkline_label(history, forecast)
    return {
        "id": zone_id,
        "state": _analytics_zone_state(zone_id, zone, active_groups, active_dampers),
        "ready": zone.get("mpc_ready") is True,
        "learning": zone.get("learn") is True,
        "accelerated_learning": zone.get("accelerated_learning") is True,
        "flags": flags,
        "badges": _model_badges(zone),
        "series": {
            "history": history,
            "forecast": forecast,
            "has_data": _has_sparkline_data(history, forecast),
            "label": label,
            "meta": "History / Now / Forecast",
        },
    }


def _analytics_zone_state(zone_id: int, zone: dict[str, Any], active_groups: set[int], active_dampers: set[int]) -> str:
    if zone.get("last_skip_reason"):
        return _title(zone.get("last_skip_reason"))
    if zone.get("mpc_ready") is True:
        return "Ready"
    if zone.get("learn") is True:
        return "Learning"
    if zone_id in active_dampers:
        return "Damper Active"
    if zone_id in active_groups:
        return "Control Zone"
    return "No Temperature Sensor"


def _model_badges(zone: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _percent_field("Progress", _scale(zone.get("learning_progress"), 100)),
        _text_field("Samples", f"{int(_first_number(zone.get('passive_samples'), zone.get('idle_samples'), 0) or 0)}/{int(_first_number(zone.get('active_samples'), 0) or 0)}"),
        _text_field("Updates", zone.get("ekf_updates") if zone.get("ekf_updates") is not None else "-"),
        _percent_field("Confidence", _scale(zone.get("confidence"), 100)),
        _temperature_field("Error", zone.get("prediction_std"), digits=2),
        _temperature_rate_field("Drift", zone.get("passive_drift_per_hour")),
        _temperature_rate_field("Response", zone.get("active_response_per_hour")),
        _temperature_rate_field("Outside", zone.get("outside_coupling_per_hour")),
    ]


def _field(label: str, value: str, *, raw: Any = None, unit: str | None = None) -> dict[str, Any]:
    return {"label": label, "value": value, "raw": raw, "unit": unit}


def _temperature_field(label: str, value: Any, *, digits: int | None = None) -> dict[str, Any]:
    number = _first_number(value)
    if number is None:
        return _field(label, "-", raw=None, unit="C")
    return _field(label, f"{number:.{digits}f} C" if digits is not None else f"{number:g} C", raw=number, unit="C")


def _temperature_rate_field(label: str, value: Any) -> dict[str, Any]:
    number = _first_number(value)
    return _field(label, "-" if number is None else f"{number:.2f} C/h", raw=number, unit="C/h")


def _percent_field(label: str, value: Any) -> dict[str, Any]:
    number = _first_number(value)
    return _field(label, "-" if number is None else f"{number:.0f}%", raw=number, unit="%")


def _hours_field(label: str, value: Any) -> dict[str, Any]:
    number = _first_number(value)
    if number is None:
        return _field(label, "-", raw=None, unit="h")
    return _field(label, f"{number:.1f} h" if number < 10 else f"{number:.0f} h", raw=number, unit="h")


def _text_field(label: str, value: Any, *, raw: Any = None) -> dict[str, Any]:
    return _field(label, str(value if value is not None and value != "" else "-"), raw=value if raw is None else raw)


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _scale(value: Any, multiplier: float) -> float | None:
    number = _first_number(value)
    return None if number is None else number * multiplier


def _id_set(value: Any) -> set[int]:
    if isinstance(value, dict):
        items = value.keys()
    elif isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = []
    result: set[int] = set()
    for item in items:
        number = _first_number(item)
        if number is not None:
            result.add(int(number))
    return result


def _sorted_ids(values: set[Any]) -> list[int]:
    result: set[int] = set()
    for value in values:
        number = _first_number(value)
        if number is not None:
            result.add(int(number))
    return sorted(result)


def _has_sparkline_data(history: list[Any], forecast: list[Any]) -> bool:
    return len(_series_values(history, ("temperature", "room_temperature", "actual", "value"))) + len(
        _series_values(forecast, ("prediction", "predicted_temperature", "predicted", "temperature", "value"))
    ) >= 2


def _sparkline_label(history: list[Any], forecast: list[Any]) -> str:
    actual = _series_values(history, ("temperature", "room_temperature", "actual", "value"))
    predicted = _series_values(forecast, ("prediction", "predicted_temperature", "predicted", "temperature", "value"))
    if not actual and not predicted:
        return "No chart data"
    if actual and predicted:
        return f"{_temp_text(actual[-1])} -> {_temp_text(predicted[-1])}"
    return f"{len(actual) + len(predicted)} points"


def _series_values(points: list[Any], keys: tuple[str, ...]) -> list[float]:
    values: list[float] = []
    for point in points:
        if isinstance(point, (int, float)) and not isinstance(point, bool):
            values.append(float(point))
            continue
        if not isinstance(point, dict):
            continue
        for key in keys:
            number = _first_number(point.get(key))
            if number is not None:
                values.append(number)
                break
    return values


def _temp_text(value: float) -> str:
    return f"{value:.1f} C" if abs(value - round(value)) > 0.0001 else f"{value:.0f} C"


def _field_by_label(surface: dict[str, Any], label: str) -> dict[str, Any]:
    fields = surface.get("fields")
    if isinstance(fields, list):
        for field in fields:
            if isinstance(field, dict) and field.get("label") == label:
                return field
    return {}


def _first_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    return value if isinstance(value, dict) else {}


def _evaluation_for_intent(evaluations: Any, intent: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(evaluations, list):
        return {}
    ac = intent.get("ac")
    for evaluation in evaluations:
        if isinstance(evaluation, dict) and evaluation.get("ac") == ac:
            return evaluation
    return _first_dict(evaluations)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _integration_state(integrations: dict[str, Any], key: str) -> dict[str, Any]:
    entry = integrations.get(key)
    if isinstance(entry, dict):
        state = entry.get("state")
        return state if isinstance(state, dict) else {}
    return {}


def _first_text(value: Any) -> str | None:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item:
                return item
    return value if isinstance(value, str) and value else None


def _count(value: Any) -> int:
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    return 0


def _first_number(*values: Any) -> float | None:
    for value in values:
        if isinstance(value, bool) or value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number == number:
            return number
    return None


def _first_series_value(mpc: dict[str, Any], key: str) -> float | None:
    runtime = _dict(mpc.get("runtime_forecast"))
    series = runtime.get("series")
    if not isinstance(series, list):
        return None
    for point in series:
        if isinstance(point, dict):
            value = _first_number(point.get(key))
            if value is not None:
                return value
    return None


def _pause_state(weather: dict[str, Any]) -> str:
    if weather.get("pause_active"):
        return "Active"
    if weather.get("pause_recommended"):
        return "Recommended"
    if weather.get("resume_pending"):
        return "Resume Pending"
    return "Clear"


def _damper_text(dampers: dict[str, Any]) -> str:
    if not dampers:
        return ""
    parts = []
    for group_id, percent in sorted(dampers.items(), key=lambda item: int(item[0])):
        number = _first_number(percent)
        parts.append(f"Zone {int(group_id) + 1} {int(round(number or 0))}%")
    return ", ".join(parts)


def _touchpad_sensor_text(hybrid: dict[str, Any]) -> str:
    sensor = hybrid.get("touchpad_sensor")
    if sensor is None:
        return "-"
    try:
        return f"0x{int(sensor):02X}"
    except (TypeError, ValueError):
        return str(sensor)


def _title(value: Any) -> str:
    text = str(value or "").replace("_", " ").replace("-", " ").strip()
    return " ".join(part[:1].upper() + part[1:].lower() for part in text.split()) or "-"
