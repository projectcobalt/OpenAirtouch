"""Threaded controller that runs AirTouchRuntime for app/API surfaces."""

from __future__ import annotations

import threading
import logging
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ..live_log import JsonlBusLogger
from ..runtime import AirTouchRuntime, RuntimeConfig, RuntimeEvent, TransportLike
from ..session.queue import TransactionSpec
from .adaptive import AdaptiveConfig, AdaptiveController
from .command_queue import RuntimeCommandQueue
from .config_store import float_or_none as _float_or_none
from .config_store import load_adaptive_config as _load_adaptive_config
from .config_store import load_adaptive_learning as _load_adaptive_learning
from .config_store import load_runtime_config as _load_runtime_config
from .config_store import save_adaptive_config as _save_adaptive_config
from .config_store import save_adaptive_learning as _save_adaptive_learning
from .config_store import save_runtime_config as _save_runtime_config
from .error_resolver import RemoteErrorResolver, RemoteErrorResolverConfig
from .event_log import EventHistory
from .event_log import controller_error_record as _controller_error_record
from .event_log import event_record as _event_record
from .event_log import frame_log_line as _frame_log_line
from .ha_client import HomeAssistantApiConfig
from .integration_loop import RuntimeIntegrationLoop, RuntimeIntegrationLoopConfig
from .integration_loop import touchpad_temperature_status as _touchpad_temperature_status
from .integrations import HomeAssistantIntegrationPoller
from .runtime_host import RuntimeHost, RuntimeHostConfig
from .transport_factory import TransportFactory, build_transport_factory

LOG = logging.getLogger("uvicorn.error")


@dataclass(frozen=True)
class RuntimeControllerConfig:
    port: str
    baudrate: int = 115200
    transport: str = "local_serial"
    tcp_host: str = "127.0.0.1"
    tcp_port: int = 6638
    runtime: RuntimeConfig = RuntimeConfig()
    bus_log: Path | None = None
    loop_sleep: float = 0.02
    reconnect_interval: float = 5.0
    event_history: int = 200
    weather: HomeAssistantApiConfig = HomeAssistantApiConfig()
    weather_poll_interval: float = 60.0
    error_resolver: RemoteErrorResolverConfig = RemoteErrorResolverConfig()
    adaptive: AdaptiveConfig = AdaptiveConfig()
    adaptive_config_path: Path | None = None
    adaptive_learning_path: Path | None = None
    runtime_config_path: Path | None = None


class RuntimeController:
    """Runs the protocol runtime in a background thread."""

    def __init__(
        self,
        config: RuntimeControllerConfig,
        *,
        transport_factory: TransportFactory | None = None,
    ) -> None:
        self.config = config
        self._transport_factory = transport_factory or self._default_transport_factory
        self._lock = threading.RLock()
        self._events = EventHistory(config.event_history)
        self._command_queue = RuntimeCommandQueue()
        self._status = "stopped"
        self._error: str | None = None
        self._integrations = HomeAssistantIntegrationPoller(
            config.weather,
            poll_interval=config.weather_poll_interval,
        )
        self._error_resolver = RemoteErrorResolver(config.error_resolver)
        self._runtime_config = _load_runtime_config(config.runtime, config.runtime_config_path)
        self._adaptive_config_path = config.adaptive_config_path
        self._adaptive = AdaptiveController(_load_adaptive_config(config.adaptive, config.adaptive_config_path))
        self._adaptive_learning_path = config.adaptive_learning_path
        self._adaptive.import_learning(_load_adaptive_learning(config.adaptive_learning_path))
        self._integration_loop = RuntimeIntegrationLoop(
            config=RuntimeIntegrationLoopConfig(adaptive_learning_path=config.adaptive_learning_path),
            integrations=self._integrations,
            adaptive=self._adaptive,
            runtime_config=lambda: self._runtime_config,
            on_changed=self._mark_changed,
            on_adaptive_event=self._record_adaptive_event,
        )
        self._host = RuntimeHost(
            config=RuntimeHostConfig(
                bus_log=config.bus_log,
                loop_sleep=config.loop_sleep,
                reconnect_interval=config.reconnect_interval,
            ),
            transport_factory=self._transport_factory,
            command_queue=self._command_queue,
            runtime_config=lambda: self._runtime_config,
            on_runtime_started=self._set_runtime,
            on_status=self._set_status,
            on_event=self._record_event,
            on_tick=self._runtime_tick,
            on_error=self._record_controller_error,
            on_stopped=self._mark_stopped,
        )

    def start(self) -> None:
        with self._lock:
            if self._host.thread_alive:
                return
            self._host.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._host.stop(timeout)

    def enqueue(self, spec: TransactionSpec) -> dict[str, Any]:
        return self._command_queue.enqueue(spec)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            runtime = self._host.runtime
            runtime_snapshot = None if runtime is None else runtime.snapshot()
            if runtime_snapshot is not None:
                _add_error_displays(runtime_snapshot, self._error_resolver)
            integrations = self._integrations.snapshot()
            integrations.update({
                "error_resolver": self._error_resolver.status(),
                "adaptive": self._adaptive.status(),
                "touchpad_temperature": _touchpad_temperature_status(self._integration_loop.touchpad_temperature),
            })
            return {
                "controller": {
                    "status": self._status,
                    "error": self._error,
                    "thread_alive": self._host.thread_alive,
                    "config": self.public_config(),
                    "datetime_sync": self._integration_loop.datetime_sync_status(runtime_snapshot),
                },
                "runtime": runtime_snapshot,
                "integrations": integrations,
            }

    def health(self) -> dict[str, Any]:
        snap = self.snapshot()
        runtime = snap["runtime"] or {}
        runtime_meta = runtime.get("runtime", {})
        connected = runtime_meta.get("connected", False)
        return {
            "ok": snap["controller"]["status"] == "running" and snap["controller"]["error"] is None and connected,
            "status": snap["controller"]["status"],
            "error": snap["controller"]["error"],
            "connected": connected,
            "address_assigned": runtime_meta.get("address_assigned", False),
            "boot_complete": runtime_meta.get("boot_complete", False),
            "protocol_mode": runtime_meta.get("protocol_mode"),
            "protocol": runtime_meta.get("protocol"),
            "protocol_name": runtime_meta.get("protocol_name"),
            "detected_protocol": runtime_meta.get("detected_protocol"),
            "protocol_mismatch": runtime_meta.get("protocol_mismatch", False),
            "protocol_latched": runtime_meta.get("protocol_latched", False),
            "protocol_detection_failed": runtime_meta.get("protocol_detection_failed", False),
            "src": runtime_meta.get("src"),
            "config": snap["controller"]["config"],
        }

    def recent_events(self) -> list[dict[str, Any]]:
        return self._events.recent()

    def change_version(self) -> int:
        return self._events.version()

    def wait_for_change(self, version: int, timeout: float = 30.0) -> int:
        return self._events.wait_for_change(version, timeout)

    def public_config(self) -> dict[str, Any]:
        return {
            "transport": self.config.transport,
            "port": self.config.port,
            "baudrate": self.config.baudrate,
            "tcp_host": self.config.tcp_host,
            "tcp_port": self.config.tcp_port,
            "reconnect_interval": self.config.reconnect_interval,
            "protocol": "auto",
            "bus_log": str(self.config.bus_log) if self.config.bus_log is not None else None,
            "fallback_touchpad_temperature": self._runtime_config.touchpad_temperature,
            "weather_entity": self.config.weather.weather_entity,
            "forecast_weather_entity": self.config.weather.forecast_weather_entity,
            "indoor_temperature_entity": self.config.weather.indoor_temperature_entity,
            "indoor_humidity_entity": self.config.weather.indoor_humidity_entity,
            "indoor_co2_entity": self.config.weather.indoor_co2_entity,
            "solar_irradiance_entity": self.config.weather.solar_irradiance_entity,
            "cloud_cover_entity": self.config.weather.cloud_cover_entity,
            "ac_power_entity": self.config.weather.ac_power_entity,
            "ac_running_entity": self.config.weather.ac_running_entity,
            "ac_frequency_entity": self.config.weather.ac_frequency_entity,
            "ac_return_air_temp_entity": self.config.weather.ac_return_air_temp_entity,
            "ac_supply_air_temp_entity": self.config.weather.ac_supply_air_temp_entity,
            "weather_poll_interval": self.config.weather_poll_interval,
            "remote_error_resolution": self.config.error_resolver.enabled,
            "remote_error_cache": (
                str(self.config.error_resolver.cache_path)
                if self.config.error_resolver.cache_path is not None
                else None
            ),
            "adaptive": self._adaptive.public_config(),
        }

    def update_runtime_config(self, values: dict[str, Any]) -> dict[str, Any]:
        temperature = _float_or_none(values.get("fallback_touchpad_temperature"))
        if temperature is None:
            temperature = _float_or_none(values.get("touchpad_temperature"))
        if temperature is None:
            raise ValueError("fallback_touchpad_temperature must be a number")
        temperature = round(min(max(temperature, 0.0), 50.0), 1)
        with self._lock:
            self._runtime_config = replace(self._runtime_config, touchpad_temperature=temperature)
            _save_runtime_config(self.config.runtime_config_path, self._runtime_config)
            self._mark_changed_locked()
            return {"fallback_touchpad_temperature": temperature}

    def update_adaptive_config(self, values: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            config = self._adaptive.update_config(values)
            _save_adaptive_config(self._adaptive_config_path, config)
            self._mark_changed_locked()
            return config

    def manage_adaptive_learning(self, values: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            learning = self._adaptive.manage_learning(values)
            _save_adaptive_learning(self._adaptive_learning_path, self._adaptive.export_learning())
            self._mark_changed_locked()
            return learning

    def _set_runtime(self, runtime: AirTouchRuntime) -> None:
        self._mark_changed_locked()

    def _set_status(self, status: str, error: str | None) -> None:
        with self._lock:
            self._status = status
            self._error = error
            self._mark_changed_locked()

    def _mark_stopped(self) -> None:
        with self._lock:
            self._status = "stopped"
            self._mark_changed_locked()
        self._error_resolver.stop()

    def _runtime_tick(self, runtime: AirTouchRuntime, _bus_logger: JsonlBusLogger) -> None:
        self._integration_loop.tick(runtime)

    def _record_event(self, event: RuntimeEvent, bus_logger: JsonlBusLogger) -> None:
        record = _event_record(event)
        self._events.append(record)
        if event.event == "rx" and event.packet is not None:
            bus_logger.log_rx(event.packet)
            LOG.info(_frame_log_line("rx", event))
        elif event.event == "tx" and event.packet is not None and event.wire is not None:
            bus_logger.log_tx(event.packet, event.wire)
            LOG.info(_frame_log_line("tx", event))
        elif event.event == "transaction" and event.transaction is not None:
            bus_logger.write(event.transaction.to_record())
        elif event.event == "status":
            bus_logger.write({"event": "runtime_status", "message": event.message})
            LOG.info("runtime status %s", event.message)

    def _record_controller_error(self, exc: Exception) -> None:
        record = _controller_error_record(exc)
        with self._lock:
            self._status = "reconnecting"
            self._error = record["message"]
            self._events.append(record)
            self._mark_changed_locked()

    def _default_transport_factory(self) -> AbstractContextManager[TransportLike]:
        return build_transport_factory(
            transport=self.config.transport,
            port=self.config.port,
            baudrate=self.config.baudrate,
            tcp_host=self.config.tcp_host,
            tcp_port=self.config.tcp_port,
        )

    def _mark_changed_locked(self) -> None:
        self._events.mark_changed()

    def _mark_changed(self) -> None:
        with self._lock:
            self._mark_changed_locked()

    def _record_adaptive_event(self, event: dict[str, Any]) -> None:
        with self._lock:
            self._events.append(event)


def _add_error_displays(runtime_snapshot: dict[str, Any], resolver: RemoteErrorResolver) -> None:
    state = runtime_snapshot.get("state") or {}
    for ac in (state.get("acs") or {}).values():
        if not isinstance(ac, dict):
            continue
        status = ac.get("status") or {}
        base = ac.get("base") or {}
        if not isinstance(status, dict) or not isinstance(base, dict):
            continue
        error = resolver.describe(base.get("brand"), status.get("error_code"))
        if error is not None:
            status["error_display"] = error


