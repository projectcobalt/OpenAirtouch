"""Runtime command queue helpers for OpenAirTouch service control."""

from __future__ import annotations

import queue

from ..runtime import AirTouchRuntime
from ..session.queue import TransactionSpec


class RuntimeCommandQueue:
    """Thread-safe queue of transactions waiting for the runtime loop."""

    def __init__(self) -> None:
        self._queue: queue.Queue[TransactionSpec] = queue.Queue()

    def enqueue(self, spec: TransactionSpec) -> dict[str, object]:
        self._queue.put(spec)
        return {
            "queued": True,
            "command": f"0x{spec.command:02X}",
            "name": spec.name,
        }

    def drain_into(self, runtime: AirTouchRuntime) -> None:
        specs: list[TransactionSpec] = []
        while True:
            try:
                specs.append(self._queue.get_nowait())
            except queue.Empty:
                break
        if specs:
            runtime.enqueue(specs)
