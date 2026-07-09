"""Runtime thread and reconnect lifecycle for the OpenAirTouch service."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Protocol

from ..live_log import JsonlBusLogger
from ..runtime import AirTouchRuntime, RuntimeConfig, RuntimeEvent
from .command_queue import RuntimeCommandQueue
from .transport_factory import TransportFactory

LOG = logging.getLogger("uvicorn.error")


class RuntimeTick(Protocol):
    def __call__(self, runtime: AirTouchRuntime, bus_logger: JsonlBusLogger) -> None:
        ...


@dataclass(frozen=True)
class RuntimeHostConfig:
    bus_log: Path | None = None
    loop_sleep: float = 0.02
    reconnect_interval: float = 5.0


class RuntimeHost:
    """Owns the live runtime thread, transport lifecycle, and reconnect loop."""

    def __init__(
        self,
        *,
        config: RuntimeHostConfig,
        transport_factory: TransportFactory,
        command_queue: RuntimeCommandQueue,
        runtime_config: Callable[[], RuntimeConfig],
        on_runtime_started: Callable[[AirTouchRuntime], None],
        on_status: Callable[[str, str | None], None],
        on_event: Callable[[RuntimeEvent, JsonlBusLogger], None],
        on_tick: RuntimeTick,
        on_error: Callable[[Exception], None],
        on_stopped: Callable[[], None],
    ) -> None:
        self.config = config
        self._transport_factory = transport_factory
        self._command_queue = command_queue
        self._runtime_config = runtime_config
        self._on_runtime_started = on_runtime_started
        self._on_status = on_status
        self._on_event = on_event
        self._on_tick = on_tick
        self._on_error = on_error
        self._on_stopped = on_stopped
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._runtime: AirTouchRuntime | None = None
        self._latched_protocol: str | None = None

    @property
    def runtime(self) -> AirTouchRuntime | None:
        return self._runtime

    @property
    def thread_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.thread_alive:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="airtouch-runtime", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

    def _run(self) -> None:
        while not self._stop.is_set():
            self._on_status("starting" if self._runtime is None else "reconnecting", None)
            try:
                with self._transport_factory() as transport, JsonlBusLogger(self.config.bus_log) as logger:
                    runtime = AirTouchRuntime(transport, self._next_runtime_config())
                    self._runtime = runtime
                    self._on_runtime_started(runtime)
                    self._on_status("running", None)
                    start_events = runtime.start()
                    self._remember_latched_protocol(runtime)
                    for event in start_events:
                        self._on_event(event, logger)
                    while not self._stop.is_set():
                        self._command_queue.drain_into(runtime)
                        for event in runtime.step():
                            self._on_event(event, logger)
                        self._on_tick(runtime, logger)
                        time.sleep(self.config.loop_sleep)
            except Exception as exc:  # pragma: no cover - exercised in live runs
                self._on_error(exc)
                self._sleep_before_reconnect()
        self._on_stopped()

    def _next_runtime_config(self) -> RuntimeConfig:
        config = self._runtime_config()
        if config.protocol.lower() == "auto" and self._latched_protocol is not None:
            return replace(config, protocol=self._latched_protocol, boot_mode="warm")
        return replace(config, boot_mode="cold")

    def _remember_latched_protocol(self, runtime: AirTouchRuntime) -> None:
        if self._latched_protocol is None and runtime.protocol_latched and runtime.detected_protocol is not None:
            self._latched_protocol = runtime.detected_protocol

    def _sleep_before_reconnect(self) -> None:
        deadline = time.monotonic() + max(0.1, self.config.reconnect_interval)
        while not self._stop.is_set() and time.monotonic() < deadline:
            time.sleep(min(0.2, deadline - time.monotonic()))
