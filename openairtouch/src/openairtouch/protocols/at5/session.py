"""AirTouch 5 session helpers.

AT5 does not share the AT4 replacement-touchscreen address probing model. The
APK treats the console as one endpoint talking to one main board, so this
session owns one console address for the lifetime of the runtime.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .packet import ADDR_CONSOLE_BASE, ADDR_EXTENSION, ADDR_MAIN_BOARD, AT5DataPack, extract_datapacks

AT5_INIT_COMMANDS: tuple[tuple[int, bytes, str], ...] = (
    (0xC045, b"", "preference"),
    (0xC051, b"", "parameters"),
    (0xC05B, b"", "service"),
    (0xC043, b"", "zone names"),
    (0xC021, b"", "zone control"),
    (0xC05D, b"", "ac settings"),
    (0xC023, b"", "ac control"),
    (0xC02B, b"", "ac timers"),
    (0x001B, bytes.fromhex("FF FF FF FD"), "gateway info"),
    (0xC055, b"", "balance"),
    (0xC059, b"", "spill"),
    (0xC057, b"", "zoning"),
    (0xC027, b"", "itc sensors"),
    (0xC02F, b"", "sensors"),
    (0xC047, b"", "password"),
    (0x0091, b"", "rsa key"),
    (0xC05F, b"", "io setting"),
    (0xC033, b"", "notice"),
)


@dataclass
class AT5Session:
    src: int = ADDR_CONSOLE_BASE
    dest: int = ADDR_MAIN_BOARD
    raw_mode: bool = True
    touchpad_temperature: float = 23.0
    touchpad_temperature_source: str = "configured"
    touchpad_temperature_detail: dict[str, Any] = field(default_factory=dict)
    heartbeat_interval: float = 60.0
    next_packet_id: int = 1
    _rx_buffer: bytearray = field(default_factory=bytearray)
    _last_heartbeat: float = field(default=0.0)

    def build_packet(self, command: int, payload: bytes = b"") -> tuple[AT5DataPack, bytes]:
        packet = AT5DataPack(
            dest=self.dest,
            src=self.src,
            packet_id=self.next_packet_id,
            command=command,
            payload=payload,
            raw_mode=self.raw_mode,
        )
        self.next_packet_id = (self.next_packet_id + 1) & 0xFF
        if self.next_packet_id == 0:
            self.next_packet_id = 1
        wire = packet.encode(stuff_raw=self.raw_mode)
        return packet, wire

    def build_packet_to(self, dest: int, command: int, payload: bytes = b"") -> tuple[AT5DataPack, bytes]:
        original_dest = self.dest
        self.dest = dest
        try:
            return self.build_packet(command, payload)
        finally:
            self.dest = original_dest

    def build_heartbeat(self) -> tuple[AT5DataPack, bytes]:
        return self.build_packet(0x0040, b"")

    def current_heartbeat_payload(self) -> bytes:
        return b""

    def set_touchpad_temperature(self, temperature: float, *, source: str = "runtime", detail: dict[str, Any] | None = None) -> None:
        self.touchpad_temperature = float(temperature)
        self.touchpad_temperature_source = source
        self.touchpad_temperature_detail = dict(detail or {})

    def build_touchpad_info_request(self) -> tuple[AT5DataPack, bytes]:
        return self.build_packet_to(ADDR_EXTENSION, 0x0061)

    def due_heartbeat(self, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        return self._last_heartbeat == 0.0 or current - self._last_heartbeat >= self.heartbeat_interval

    def mark_heartbeat_sent(self, now: float | None = None) -> None:
        self._last_heartbeat = time.monotonic() if now is None else now

    def feed_rx(self, data: bytes) -> list[AT5DataPack]:
        self._rx_buffer.extend(data)
        packets = extract_datapacks(bytes(self._rx_buffer))
        if packets:
            last = packets[-1]
            consumed = last.stream_offset + len(last.encode(raw_mode=last.raw_mode))
            del self._rx_buffer[:consumed]
        elif len(self._rx_buffer) > 8192:
            del self._rx_buffer[:-1024]
        return packets

    def choose_available_address(
        self,
        *,
        require_evidence: bool = False,
        allow_shared_secondary: bool = False,
    ) -> int | None:
        return self.src

    def occupied_touchpad_addresses(self) -> list[int]:
        return []
