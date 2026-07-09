"""Runtime integration loop for OpenAirTouch service-side inputs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .. import commands
from ..constants import ADDR_TOUCHPAD_1
from ..runtime import AirTouchRuntime, RuntimeConfig
from ..session.queue import TransactionSpec
from .adaptive import AdaptiveController
from .config_store import save_adaptive_learning as _save_adaptive_learning
from .integrations import HomeAssistantIntegrationPoller
from .touchpad_temperature import TouchpadTemperatureResult, resolve_touchpad_temperature

DATETIME_SYNC_INTERVAL = 60.0


@dataclass(frozen=True)
class RuntimeIntegrationLoopConfig:
    adaptive_learning_path: Path | None = None


class RuntimeIntegrationLoop:
    """Coordinates non-protocol service work that runs beside the runtime."""

    def __init__(
        self,
        *,
        config: RuntimeIntegrationLoopConfig,
        integrations: HomeAssistantIntegrationPoller,
        adaptive: AdaptiveController,
        runtime_config: Callable[[], RuntimeConfig],
        on_changed: Callable[[], None],
        on_adaptive_event: Callable[[dict[str, Any]], None],
    ) -> None:
        self.config = config
        self._integrations = integrations
        self._adaptive = adaptive
        self._runtime_config = runtime_config
        self._on_changed = on_changed
        self._on_adaptive_event = on_adaptive_event
        self.touchpad_temperature = TouchpadTemperatureResult(
            temperature=self._runtime_config().touchpad_temperature,
            source="configured",
            detail={},
        )
        self._next_adaptive_learning_save = 0.0
        self._next_datetime_sync = 0.0
        self._last_datetime_sync: dict[str, Any] | None = None
        self._datetime_sync_error: str | None = None

    def tick(self, runtime: AirTouchRuntime) -> None:
        self.poll_weather()
        self.run_adaptive(runtime)
        self.update_touchpad_temperature(runtime)
        self.sync_datetime_if_due(runtime)

    def poll_weather(self) -> None:
        if self._integrations.poll():
            self._on_changed()

    def run_adaptive(self, runtime: AirTouchRuntime) -> None:
        runtime_snapshot = runtime.snapshot()
        integrations = self._integrations.runtime_inputs()
        specs = self._adaptive.evaluate(runtime_snapshot, integrations)
        if specs:
            self.save_adaptive_learning_now()
        else:
            self.save_adaptive_learning_periodically()
        if not specs:
            return
        runtime.enqueue(specs)
        for spec in specs:
            self._on_adaptive_event({
                "event": "adaptive",
                "message": f"queued {spec.name}",
                "command": f"0x{spec.command:02X}",
                "state_changed": False,
            })
        self._on_changed()

    def update_touchpad_temperature(self, runtime: AirTouchRuntime) -> None:
        runtime_snapshot = runtime.snapshot()
        integrations = self._integrations.indoor_input()
        result = resolve_touchpad_temperature(
            runtime_snapshot,
            integrations,
            self._adaptive.status(),
            fallback=self._runtime_config().touchpad_temperature,
        )
        previous = self.touchpad_temperature
        runtime.set_touchpad_temperature(result.temperature, source=result.source, detail=result.detail)
        if (
            previous.temperature == result.temperature
            and previous.source == result.source
            and previous.detail == result.detail
        ):
            return
        self.touchpad_temperature = result
        self._on_changed()

    def sync_datetime_if_due(self, runtime: AirTouchRuntime) -> None:
        now = time.monotonic()
        if now < self._next_datetime_sync:
            return
        self._next_datetime_sync = now + DATETIME_SYNC_INTERVAL
        session = runtime.session
        if session is None or not runtime.address_assigned or session.src != ADDR_TOUCHPAD_1:
            return

        try:
            clock, time_zone, source = self._clock_now()
            payload = datetime_payload(clock)
            spec = TransactionSpec.from_command(
                commands.datetime_command(**payload),
                name="datetime_sync",
            )
            runtime.enqueue([spec])
            self._last_datetime_sync = {
                "last_queued_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "synced_time": clock.isoformat(timespec="seconds"),
                "time_zone": time_zone,
                "source": source,
                "touchpad_address": f"0x{session.src:02X}",
                "command": "0x40",
                "payload": payload,
            }
            self._datetime_sync_error = None
            self._on_changed()
        except Exception as exc:  # pragma: no cover - defensive live clock path
            self._datetime_sync_error = f"{type(exc).__name__}: {exc}"
            self._on_changed()

    def datetime_sync_status(self, runtime_snapshot: dict[str, Any] | None) -> dict[str, Any]:
        runtime = (runtime_snapshot or {}).get("runtime") or {}
        source_address = runtime.get("src")
        current = datetime.now().astimezone()
        status: dict[str, Any] = {
            "enabled": source_address == f"0x{ADDR_TOUCHPAD_1:02X}",
            "source_address": source_address,
            "required_source_address": f"0x{ADDR_TOUCHPAD_1:02X}",
            "current_time": current.isoformat(timespec="seconds"),
            "time_zone": current.tzname() or str(current.tzinfo or "local"),
            "interval_seconds": int(DATETIME_SYNC_INTERVAL),
            "error": self._datetime_sync_error,
        }
        if self._last_datetime_sync is not None:
            status.update(self._last_datetime_sync)
        return status

    def save_adaptive_learning_periodically(self) -> None:
        if self.config.adaptive_learning_path is None:
            return
        now = time.monotonic()
        if now < self._next_adaptive_learning_save:
            return
        self._next_adaptive_learning_save = now + 60.0
        self.save_adaptive_learning_now()

    def save_adaptive_learning_now(self) -> None:
        if self.config.adaptive_learning_path is None:
            return
        self._next_adaptive_learning_save = time.monotonic() + 60.0
        _save_adaptive_learning(self.config.adaptive_learning_path, self._adaptive.export_learning())

    def _clock_now(self) -> tuple[datetime, str, str]:
        time_zone = self._integrations.home_assistant_timezone()
        if time_zone:
            try:
                clock = datetime.now(ZoneInfo(time_zone))
                return clock, time_zone, "home_assistant"
            except ZoneInfoNotFoundError:
                pass
        clock = datetime.now().astimezone()
        zone_name = clock.tzname() or str(clock.tzinfo or "local")
        return clock, zone_name, "host"


def touchpad_temperature_status(result: TouchpadTemperatureResult) -> dict[str, Any]:
    return {
        "temperature": result.temperature,
        "source": result.source,
        "detail": dict(result.detail),
    }


def datetime_payload(clock: datetime) -> dict[str, int]:
    return {
        "year": clock.year,
        "month": clock.month,
        "day": clock.day,
        "weekday": clock.isoweekday() % 7 + 1,
        "hour": clock.hour,
        "minute": clock.minute,
        "second": clock.second,
    }
