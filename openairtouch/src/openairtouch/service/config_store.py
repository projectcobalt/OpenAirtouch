"""Persistence helpers for OpenAirTouch service configuration."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import Path
from typing import Any

from ..runtime import RuntimeConfig
from .adaptive import AdaptiveConfig, AdaptiveController

LOG = logging.getLogger("uvicorn.error")


def load_adaptive_config(default: AdaptiveConfig, path: Path | None) -> AdaptiveConfig:
    if path is None:
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("Could not load adaptive config from %s: %s", path, exc)
        return default
    if not isinstance(payload, dict):
        LOG.warning("Ignoring adaptive config from %s because it is not an object", path)
        return default
    fields = default.__dataclass_fields__
    data = {name: getattr(default, name) for name in fields}
    data.update({key: value for key, value in payload.items() if key in fields})
    try:
        return AdaptiveController(AdaptiveConfig(**data)).config
    except (TypeError, ValueError) as exc:
        LOG.warning("Ignoring invalid adaptive config from %s: %s", path, exc)
        return default


def save_adaptive_config(path: Path | None, config: dict[str, Any]) -> None:
    if path is None:
        return
    allowed = AdaptiveConfig.__dataclass_fields__
    payload = {key: config[key] for key in allowed if key in config}
    _write_json(path, payload, indent=2, sort_keys=True, warning_label="adaptive config")


def load_adaptive_learning(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("Could not load adaptive learning data from %s: %s", path, exc)
        return {}
    return payload if isinstance(payload, dict) else {}


def save_adaptive_learning(path: Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        return
    _write_json(path, payload, separators=(",", ":"), sort_keys=True, warning_label="adaptive learning data")


def load_runtime_config(default: RuntimeConfig, path: Path | None) -> RuntimeConfig:
    if path is None:
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("Could not load runtime config from %s: %s", path, exc)
        return default
    if not isinstance(payload, dict):
        LOG.warning("Ignoring runtime config from %s because it is not an object", path)
        return default
    temperature = float_or_none(payload.get("fallback_touchpad_temperature"))
    if temperature is None:
        temperature = float_or_none(payload.get("touchpad_temperature"))
    if temperature is None:
        return default
    return replace(default, touchpad_temperature=round(min(max(temperature, 0.0), 50.0), 1))


def save_runtime_config(path: Path | None, config: RuntimeConfig) -> None:
    if path is None:
        return
    payload = {"fallback_touchpad_temperature": config.touchpad_temperature}
    _write_json(path, payload, indent=2, sort_keys=True, warning_label="runtime config")


def float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _write_json(path: Path, payload: dict[str, Any], *, warning_label: str, **json_kwargs: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.tmp")
        temp_path.write_text(json.dumps(payload, **json_kwargs), encoding="utf-8")
        temp_path.replace(path)
    except OSError as exc:
        LOG.warning("Could not save %s to %s: %s", warning_label, path, exc)
