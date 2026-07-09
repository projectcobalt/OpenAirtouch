"""Event history and change notification helpers for the service layer."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any

from ..packet import PacketParseError, parse_packet
from ..runtime import RuntimeEvent
from .event_text import describe_event


class EventHistory:
    """Stores recent service events and wakes websocket/API waiters."""

    def __init__(self, history_limit: int) -> None:
        self._condition = threading.Condition(threading.RLock())
        self._version = 0
        self._events: deque[dict[str, Any]] = deque(maxlen=history_limit)

    def append(self, record: dict[str, Any]) -> None:
        with self._condition:
            self._events.append(record)
            self._mark_changed_locked()

    def mark_changed(self) -> None:
        with self._condition:
            self._mark_changed_locked()

    def recent(self) -> list[dict[str, Any]]:
        with self._condition:
            return list(self._events)

    def version(self) -> int:
        with self._condition:
            return self._version

    def wait_for_change(self, version: int, timeout: float = 30.0) -> int:
        with self._condition:
            if self._version <= version:
                self._condition.wait(timeout)
            return self._version

    def _mark_changed_locked(self) -> None:
        self._version += 1
        self._condition.notify_all()


def controller_error_record(exc: Exception) -> dict[str, Any]:
    message = f"{type(exc).__name__}: {exc}"
    record = {
        "event": "controller",
        "message": message,
        "state_changed": False,
    }
    plain = describe_event(record)
    record["plain"] = plain
    record["summary"] = plain["text"]
    return record


def event_record(event: RuntimeEvent) -> dict[str, Any]:
    record: dict[str, Any] = {
        "event": event.event,
        "message": event.message,
        "state_changed": event.state_changed,
    }
    packet = event_packet_for_log(event)
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
    if not record["message"]:
        record["message"] = plain["text"]
    return record


def frame_log_line(direction: str, event: RuntimeEvent) -> str:
    packet = event_packet_for_log(event)
    if packet is None:
        return f"bus {direction} packet=none"
    return (
        f"bus {direction} "
        f"src=0x{packet.src:02X} dest=0x{packet.dest:02X} "
        f"cmd=0x{packet.command:02X} {packet.command_name} "
        f"id={packet.packet_id} len={len(packet.payload)} crc_ok={packet.crc_ok} "
        f"payload={packet.payload.hex(' ').upper()}"
    )


def event_packet_for_log(event: RuntimeEvent) -> Any:
    if event.event == "tx" and event.wire is not None:
        try:
            return parse_packet(event.wire)
        except PacketParseError:
            return event.packet
    return event.packet
