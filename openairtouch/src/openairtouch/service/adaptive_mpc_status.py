"""Status projection helpers for adaptive MPC learning."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def mpc_status(
    *,
    zone_models: Mapping[int, Any],
    compressor: Any,
    history: Mapping[int, Any],
    forecasts: Mapping[int, list[dict[str, Any]]],
    last_plans: Mapping[int, Any],
    learning_paused_reason: str | None,
    now: float,
    mode_idle: str,
    plan_dt_minutes: float,
    learning_observation_interval_seconds: float,
) -> dict[str, Any]:
    return {
        "zones": {
            str(group_id): _zone_status(
                model,
                history_points=len(history.get(group_id, ())),
                mode_idle=mode_idle,
                plan_dt_minutes=plan_dt_minutes,
                learning_observation_interval_seconds=learning_observation_interval_seconds,
            )
            for group_id, model in sorted(zone_models.items())
        },
        "compressor": compressor.status(now),
        "learning_paused_reason": learning_paused_reason,
        "analytics": {
            str(group_id): [_analytics_point(point) for point in list(points)[-24:]]
            for group_id, points in sorted(history.items())
        },
        "forecasts": {
            str(group_id): points
            for group_id, points in sorted(forecasts.items())
            if points
        },
        "plans": {
            str(ac_id): _plan_status(plan)
            for ac_id, plan in sorted(last_plans.items())
        },
    }


def _zone_status(
    model: Any,
    *,
    history_points: int,
    mode_idle: str,
    plan_dt_minutes: float,
    learning_observation_interval_seconds: float,
) -> dict[str, Any]:
    return {
        "learn": model.learn,
        "accelerated_learning": model.accelerated_learning,
        "learning_progress": model.learning_progress,
        "readiness_reason": model.readiness_reason,
        "cooling_readiness_reason": model.readiness_reason_for(cooling=True),
        "heating_readiness_reason": model.readiness_reason_for(cooling=False),
        "readiness_requirements": model._readiness_requirements(),
        "cooling_ready": model.cooling_ready,
        "heating_ready": model.heating_ready,
        "idle_observations": model.ekf.idle_samples,
        "cooling_observations": model.ekf.cooling_samples,
        "heating_observations": model.ekf.heating_samples,
        "skipped_observations": model.skipped_observations,
        "last_skip_reason": model.last_skip_reason,
        "last_boost_ts": model.last_boost_ts,
        "passive_hours": round(model.passive_samples * learning_observation_interval_seconds / 3600.0, 2),
        "active_hours": round(model.active_samples * learning_observation_interval_seconds / 3600.0, 2),
        "confidence": model.confidence,
        "mpc_ready": model.mpc_ready,
        "passive_samples": model.passive_samples,
        "active_samples": model.active_samples,
        "last_temperature": model.last_temperature,
        "last_ts": model.last_ts,
        "passive_drift_per_hour": round(model.passive_drift_per_hour, 3),
        "active_response_per_hour": round(model.active_response_per_hour, 3),
        "outside_coupling_per_hour": round(model.outside_coupling_per_hour, 4),
        "ekf_updates": model.ekf.updates,
        "idle_samples": model.ekf.idle_samples,
        "heating_samples": model.ekf.heating_samples,
        "cooling_samples": model.ekf.cooling_samples,
        "prediction_std": round(model.ekf.prediction_std(mode_idle, model.ekf.x[0], model.ekf.x[0], plan_dt_minutes), 3),
        "alpha": round(model.ekf.x[1], 4),
        "beta_heat": round(model.ekf.x[2], 3),
        "beta_cool": round(model.ekf.x[3], 3),
        "beta_solar": round(model.ekf.x[4], 3),
        "beta_occupancy": round(model.ekf.x[5], 3),
        "covariance": {
            "temperature": round(model.ekf.p[0][0], 4),
            "alpha": round(model.ekf.p[1][1], 4),
            "heat": round(model.ekf.p[2][2], 4),
            "cool": round(model.ekf.p[3][3], 4),
            "solar": round(model.ekf.p[4][4], 4),
            "occupancy": round(model.ekf.p[5][5], 4),
        },
        "history_points": history_points,
    }


def _plan_status(plan: Any) -> dict[str, Any]:
    return {
        "target": plan.target,
        "source": plan.source,
        "confidence": plan.confidence,
        "action": plan.action,
        "power_fraction": plan.power_fraction,
        "projected_runtime_hours": plan.projected_runtime_hours,
        "zone_projected_runtime_hours": {
            str(group_id): hours
            for group_id, hours in plan.zone_projected_runtime_hours.items()
        },
        "predicted_temperatures": plan.predicted_temperatures,
        "reason": plan.reason,
        "runtime_forecast": runtime_forecast_status(plan.runtime_forecast),
    }


def _analytics_point(point: dict[str, Any]) -> dict[str, Any]:
    temperature = _number(point.get("temperature"))
    if temperature is None:
        temperature = _number(point.get("room_temp"))
    outdoor_temperature = _number(point.get("outdoor_temperature"))
    if outdoor_temperature is None:
        outdoor_temperature = _number(point.get("outdoor_temp"))
    result: dict[str, Any] = {
        "ts": point.get("ts"),
        "temperature": temperature,
        "outdoor_temperature": outdoor_temperature,
        "mode": point.get("mode"),
        "source": point.get("source"),
        "skipped": point.get("skipped") is True,
        "skip_reason": point.get("skip_reason"),
    }
    q_solar = _number(point.get("q_solar"))
    if q_solar is not None:
        result["q_solar"] = q_solar
    estimated_power_fraction = _number(point.get("estimated_power_fraction"))
    if estimated_power_fraction is not None:
        result["estimated_power_fraction"] = estimated_power_fraction
    predicted = _number(point.get("predicted_temperature"))
    if predicted is None:
        predicted = _number(point.get("prediction"))
    if predicted is not None:
        result["predicted_temperature"] = predicted
    return result


def runtime_forecast_status(forecast: Any | None) -> dict[str, Any] | None:
    if forecast is None:
        return None
    return {
        "horizon_hours": forecast.horizon_hours,
        "step_minutes": forecast.step_minutes,
        "runtime_minutes": forecast.runtime_minutes,
        "runtime_hours": round(forecast.runtime_minutes / 60.0, 2),
        "runtime_fraction": forecast.runtime_fraction,
        "zone_runtime_minutes": {
            str(group_id): minutes
            for group_id, minutes in forecast.zone_runtime_minutes.items()
        },
        "zone_runtime_fraction": {
            str(group_id): fraction
            for group_id, fraction in forecast.zone_runtime_fraction.items()
        },
        "action_windows": forecast.action_windows,
        "series": forecast.series,
        "quality": forecast.quality,
    }


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None
