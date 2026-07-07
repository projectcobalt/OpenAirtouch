"""Threaded controller that runs AirTouchRuntime for app/API surfaces."""

from __future__ import annotations

import json
import queue
import threading
import time
import logging
from collections import deque
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .. import commands
from ..constants import ADDR_TOUCHPAD_1
from ..live_log import JsonlBusLogger
from ..packet import PacketParseError, parse_packet
from ..runtime import AirTouchRuntime, RuntimeConfig, RuntimeEvent, TransportLike
from ..session.queue import TransactionSpec
from ..transport import SerialConfig, SerialRs485Transport, TcpSerialConfig, TcpSerialTransport
from .adaptive import AdaptiveConfig, AdaptiveController
from .error_resolver import RemoteErrorResolver, RemoteErrorResolverConfig
from .event_text import describe_event
from .ha_client import HomeAssistantApiConfig
from .integrations import HomeAssistantIntegrationPoller
from .touchpad_temperature import TouchpadTemperatureResult, resolve_touchpad_temperature

TransportFactory = Callable[[], AbstractContextManager[TransportLike]]
LOG = logging.getLogger("uvicorn.error")
DATETIME_SYNC_INTERVAL = 60.0


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
    ui_theme: str = "system"
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
        self._change = threading.Condition(self._lock)
        self._change_version = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._runtime: AirTouchRuntime | None = None
        self._events: deque[dict[str, Any]] = deque(maxlen=config.event_history)
        self._command_queue: queue.Queue[TransactionSpec] = queue.Queue()
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
        self._next_adaptive_learning_save = 0.0
        self._touchpad_temperature = TouchpadTemperatureResult(
            temperature=self._runtime_config.touchpad_temperature,
            source="raw_payload" if self._runtime_config.heartbeat_payload is not None else "configured",
            detail={"override": True} if self._runtime_config.heartbeat_payload is not None else {},
        )
        self._next_datetime_sync = 0.0
        self._last_datetime_sync: dict[str, Any] | None = None
        self._datetime_sync_error: str | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name="airtouch-runtime", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

    def enqueue(self, spec: TransactionSpec) -> dict[str, Any]:
        self._command_queue.put(spec)
        return {
            "queued": True,
            "command": f"0x{spec.command:02X}",
            "name": spec.name,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            runtime_snapshot = None if self._runtime is None else self._runtime.snapshot()
            if runtime_snapshot is not None:
                _add_error_displays(runtime_snapshot, self._error_resolver)
            integrations = self._integrations.snapshot()
            integrations.update({
                "error_resolver": self._error_resolver.status(),
                "adaptive": self._adaptive.status(),
                "touchpad_temperature": _touchpad_temperature_status(self._touchpad_temperature),
            })
            return {
                "controller": {
                    "status": self._status,
                    "error": self._error,
                    "thread_alive": self._thread is not None and self._thread.is_alive(),
                    "config": self.public_config(),
                    "datetime_sync": self._datetime_sync_status(runtime_snapshot),
                },
                "runtime": runtime_snapshot,
                "integrations": integrations,
            }

    def health(self) -> dict[str, Any]:
        snap = self.snapshot()
        runtime = snap["runtime"] or {}
        runtime_meta = runtime.get("runtime", {})
        return {
            "ok": snap["controller"]["status"] == "running" and snap["controller"]["error"] is None,
            "status": snap["controller"]["status"],
            "error": snap["controller"]["error"],
            "connected": runtime_meta.get("connected", False),
            "address_assigned": runtime_meta.get("address_assigned", False),
            "boot_complete": runtime_meta.get("boot_complete", False),
            "protocol_mode": runtime_meta.get("protocol_mode"),
            "protocol": runtime_meta.get("protocol"),
            "protocol_name": runtime_meta.get("protocol_name"),
            "detected_protocol": runtime_meta.get("detected_protocol"),
            "protocol_mismatch": runtime_meta.get("protocol_mismatch", False),
            "src": runtime_meta.get("src"),
            "config": snap["controller"]["config"],
        }

    def recent_events(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events)

    def change_version(self) -> int:
        with self._lock:
            return self._change_version

    def wait_for_change(self, version: int, timeout: float = 30.0) -> int:
        with self._change:
            if self._change_version <= version:
                self._change.wait(timeout)
            return self._change_version

    def public_config(self) -> dict[str, Any]:
        return {
            "transport": self.config.transport,
            "port": self.config.port,
            "baudrate": self.config.baudrate,
            "tcp_host": self.config.tcp_host,
            "tcp_port": self.config.tcp_port,
            "reconnect_interval": self.config.reconnect_interval,
            "protocol": self._runtime_config.protocol,
            "bus_log": str(self.config.bus_log) if self.config.bus_log is not None else None,
            "ui_theme": self.config.ui_theme,
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

    def _run(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                self._status = "starting" if self._runtime is None else "reconnecting"
                self._mark_changed_locked()
            try:
                with self._transport_factory() as transport, JsonlBusLogger(self.config.bus_log) as logger:
                    runtime = AirTouchRuntime(transport, self._runtime_config)
                    with self._lock:
                        self._runtime = runtime
                        self._status = "running"
                        self._error = None
                        self._mark_changed_locked()
                    for event in runtime.start():
                        self._record_event(event, logger)
                    while not self._stop.is_set():
                        self._drain_commands(runtime)
                        for event in runtime.step():
                            self._record_event(event, logger)
                        self._poll_weather()
                        self._run_adaptive(runtime)
                        self._update_touchpad_temperature(runtime)
                        self._sync_datetime_if_due(runtime)
                        time.sleep(self.config.loop_sleep)
            except Exception as exc:  # pragma: no cover - exercised in live runs
                self._record_controller_error(exc)
                self._sleep_before_reconnect()
        with self._lock:
            self._status = "stopped"
            self._mark_changed_locked()
        self._error_resolver.stop()

    def _drain_commands(self, runtime: AirTouchRuntime) -> None:
        specs = []
        while True:
            try:
                specs.append(self._command_queue.get_nowait())
            except queue.Empty:
                break
        if specs:
            runtime.enqueue(specs)

    def _record_event(self, event: RuntimeEvent, bus_logger: JsonlBusLogger) -> None:
        record = _event_record(event)
        with self._lock:
            self._events.append(record)
            self._mark_changed_locked()
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
        message = f"{type(exc).__name__}: {exc}"
        record = {
            "event": "controller",
            "message": message,
            "state_changed": False,
        }
        plain = describe_event(record)
        record["plain"] = plain
        record["summary"] = plain["text"]
        with self._lock:
            self._status = "reconnecting"
            self._error = message
            self._events.append(record)
            self._mark_changed_locked()

    def _poll_weather(self) -> None:
        if self._integrations.poll():
            with self._lock:
                self._mark_changed_locked()

    def _run_adaptive(self, runtime: AirTouchRuntime) -> None:
        runtime_snapshot = runtime.snapshot()
        integrations = self._integrations.runtime_inputs()
        specs = self._adaptive.evaluate(runtime_snapshot, integrations)
        if specs:
            self._save_adaptive_learning_now()
        else:
            self._save_adaptive_learning_periodically()
        if specs:
            runtime.enqueue(specs)
            with self._lock:
                for spec in specs:
                    self._events.append({
                        "event": "adaptive",
                        "message": f"queued {spec.name}",
                        "command": f"0x{spec.command:02X}",
                        "state_changed": False,
                    })
                self._mark_changed_locked()

    def _update_touchpad_temperature(self, runtime: AirTouchRuntime) -> None:
        if self._runtime_config.heartbeat_payload is not None:
            return
        runtime_snapshot = runtime.snapshot()
        integrations = self._integrations.indoor_input()
        result = resolve_touchpad_temperature(
            runtime_snapshot,
            integrations,
            self._adaptive.status(),
            fallback=self._runtime_config.touchpad_temperature,
        )
        previous = self._touchpad_temperature
        runtime.set_touchpad_temperature(result.temperature, source=result.source, detail=result.detail)
        if (
            previous.temperature == result.temperature
            and previous.source == result.source
            and previous.detail == result.detail
        ):
            return
        with self._lock:
            self._touchpad_temperature = result
            self._mark_changed_locked()

    def _sync_datetime_if_due(self, runtime: AirTouchRuntime) -> None:
        now = time.monotonic()
        if now < self._next_datetime_sync:
            return
        self._next_datetime_sync = now + DATETIME_SYNC_INTERVAL
        session = runtime.session
        if session is None or not runtime.address_assigned or session.src != ADDR_TOUCHPAD_1:
            return

        try:
            clock, time_zone, source = self._clock_now()
            payload = _datetime_payload(clock)
            spec = TransactionSpec.from_command(
                commands.datetime_command(**payload),
                name="datetime_sync",
            )
            runtime.enqueue([spec])
            status = {
                "last_queued_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "synced_time": clock.isoformat(timespec="seconds"),
                "time_zone": time_zone,
                "source": source,
                "touchpad_address": f"0x{session.src:02X}",
                "command": "0x40",
                "payload": payload,
            }
            with self._lock:
                self._last_datetime_sync = status
                self._datetime_sync_error = None
                self._mark_changed_locked()
        except Exception as exc:  # pragma: no cover - defensive live clock path
            with self._lock:
                self._datetime_sync_error = f"{type(exc).__name__}: {exc}"
                self._mark_changed_locked()

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

    def _datetime_sync_status(self, runtime_snapshot: dict[str, Any] | None) -> dict[str, Any]:
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

    def _save_adaptive_learning_periodically(self) -> None:
        if self._adaptive_learning_path is None:
            return
        now = time.monotonic()
        if now < self._next_adaptive_learning_save:
            return
        self._next_adaptive_learning_save = now + 60.0
        self._save_adaptive_learning_now()

    def _save_adaptive_learning_now(self) -> None:
        if self._adaptive_learning_path is None:
            return
        self._next_adaptive_learning_save = time.monotonic() + 60.0
        _save_adaptive_learning(self._adaptive_learning_path, self._adaptive.export_learning())

    def _sleep_before_reconnect(self) -> None:
        deadline = time.monotonic() + max(0.1, self.config.reconnect_interval)
        while not self._stop.is_set() and time.monotonic() < deadline:
            time.sleep(min(0.2, deadline - time.monotonic()))

    def _default_transport_factory(self) -> AbstractContextManager[TransportLike]:
        if self.config.transport == "local_serial":
            return SerialRs485Transport(SerialConfig(port=self.config.port, baudrate=self.config.baudrate))
        if self.config.transport == "tcp_serial":
            return TcpSerialTransport(TcpSerialConfig(host=self.config.tcp_host, port=self.config.tcp_port))
        raise ValueError(f"unsupported transport: {self.config.transport}")

    def _mark_changed_locked(self) -> None:
        self._change_version += 1
        self._change.notify_all()


def _event_record(event: RuntimeEvent) -> dict[str, Any]:
    record: dict[str, Any] = {
        "event": event.event,
        "message": event.message,
        "state_changed": event.state_changed,
    }
    packet = _event_packet_for_log(event)
    if packet is not None:
        record.update({
            "direction": event.direction,
            "src": f"0x{packet.src:02X}",
            "dest": f"0x{packet.dest:02X}",
            "cmd": f"0x{packet.command:02X}",
            "cmd_name": packet.command_name,
            "packet_id": packet.packet_id,
            "len": len(packet.payload),
            "crc_ok": packet.crc_ok,
            "decoded": event.decoded,
        })
    if event.transaction is not None:
        record["transaction"] = event.transaction.to_record()
    plain = describe_event(record)
    record["plain"] = plain
    record["summary"] = plain["text"]
    return record


def _touchpad_temperature_status(result: TouchpadTemperatureResult) -> dict[str, Any]:
    return {
        "temperature": result.temperature,
        "source": result.source,
        "detail": dict(result.detail),
    }


def _datetime_payload(clock: datetime) -> dict[str, int]:
    return {
        "year": clock.year,
        "month": clock.month,
        "day": clock.day,
        "weekday": clock.isoweekday() % 7 + 1,
        "hour": clock.hour,
        "minute": clock.minute,
        "second": clock.second,
    }


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _frame_log_line(direction: str, event: RuntimeEvent) -> str:
    packet = _event_packet_for_log(event)
    if packet is None:
        return f"bus {direction} packet=none"
    return (
        f"bus {direction} "
        f"src=0x{packet.src:02X} dest=0x{packet.dest:02X} "
        f"cmd=0x{packet.command:02X} {packet.command_name} "
        f"id={packet.packet_id} len={len(packet.payload)} crc_ok={packet.crc_ok} "
        f"payload={packet.payload.hex(' ').upper()}"
    )


def _event_packet_for_log(event: RuntimeEvent) -> Any:
    if event.event == "tx" and event.wire is not None:
        try:
            return parse_packet(event.wire)
        except PacketParseError:
            return event.packet
    return event.packet


def _load_adaptive_config(default: AdaptiveConfig, path: Path | None) -> AdaptiveConfig:
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


def _load_runtime_config(default: RuntimeConfig, path: Path | None) -> RuntimeConfig:
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
    temperature = _float_or_none(payload.get("fallback_touchpad_temperature"))
    if temperature is None:
        temperature = _float_or_none(payload.get("touchpad_temperature"))
    if temperature is None:
        return default
    return replace(default, touchpad_temperature=round(min(max(temperature, 0.0), 50.0), 1))


def _save_runtime_config(path: Path | None, config: RuntimeConfig) -> None:
    if path is None:
        return
    payload = {"fallback_touchpad_temperature": config.touchpad_temperature}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.tmp")
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(path)
    except OSError as exc:
        LOG.warning("Could not save runtime config to %s: %s", path, exc)


def _save_adaptive_config(path: Path | None, config: dict[str, Any]) -> None:
    if path is None:
        return
    allowed = AdaptiveConfig.__dataclass_fields__
    payload = {key: config[key] for key in allowed if key in config}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.tmp")
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(path)
    except OSError as exc:
        LOG.warning("Could not save adaptive config to %s: %s", path, exc)


def _load_adaptive_learning(path: Path | None) -> dict[str, Any]:
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


def _save_adaptive_learning(path: Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.tmp")
        temp_path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True), encoding="utf-8")
        temp_path.replace(path)
    except OSError as exc:
        LOG.warning("Could not save adaptive learning data to %s: %s", path, exc)
