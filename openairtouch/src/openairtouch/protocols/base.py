"""Protocol contracts for OpenAirTouch runtime integration."""

from __future__ import annotations

from typing import Any, Iterable, Protocol, runtime_checkable
from ..session.init import InitStep
from ..session.queue import TransactionSpec


@runtime_checkable
class ProtocolPacket(Protocol):
    dest: int
    src: int
    packet_id: int
    command: int
    payload: bytes
    raw_mode: bool
    stream_offset: int

    @property
    def crc_ok(self) -> bool:
        ...

    @property
    def command_name(self) -> str:
        ...

    @property
    def dest_name(self) -> str:
        ...

    @property
    def src_name(self) -> str:
        ...

    def encode(self, *, raw_mode: bool | None = None, stuff_raw: bool = False) -> bytes:
        ...

    def to_record(self) -> dict:
        ...


class ProtocolSession(Protocol):
    src: int
    dest: int
    touchpad_temperature: float
    touchpad_temperature_source: str
    touchpad_temperature_detail: dict[str, Any]

    def build_packet(self, command: int, payload: bytes = b"") -> tuple[ProtocolPacket, bytes]:
        ...

    def build_heartbeat(self) -> tuple[ProtocolPacket, bytes]:
        ...

    def current_heartbeat_payload(self) -> bytes:
        ...

    def set_touchpad_temperature(self, temperature: float, *, source: str = "runtime", detail: dict[str, Any] | None = None) -> None:
        ...

    def build_touchpad_info_request(self) -> tuple[ProtocolPacket, bytes]:
        ...

    def due_heartbeat(self, now: float | None = None) -> bool:
        ...

    def mark_heartbeat_sent(self, now: float | None = None) -> None:
        ...

    def feed_rx(self, data: bytes) -> list[ProtocolPacket]:
        ...

    def choose_available_address(
        self,
        *,
        require_evidence: bool = False,
        allow_shared_secondary: bool = False,
    ) -> int | None:
        ...

    def occupied_touchpad_addresses(self) -> list[int]:
        ...


class ProtocolState(Protocol):
    last_command: int | None

    def apply_decoded(self, command: int, decoded: dict[str, Any]) -> None:
        ...

    def snapshot(self) -> dict[str, Any]:
        ...


class ProtocolCommandError(ValueError):
    """Raised when a command intent is not supported by the active protocol."""


class ProtocolProfile(Protocol):
    name: str
    display_name: str

    def create_session(self, *, touchpad_temperature: float, heartbeat_interval: float) -> ProtocolSession:
        ...

    def create_state(self) -> ProtocolState:
        ...

    def decode_payload(self, command: int, payload: bytes) -> dict[str, Any]:
        ...

    def decode_packet(self, packet: ProtocolPacket) -> dict[str, Any]:
        ...

    def build_transaction(self, action: str, data: dict[str, Any], *, state: dict[str, Any] | None = None) -> TransactionSpec:
        ...

    def init_steps(self) -> list[InitStep]:
        ...

    def init_transactions(self) -> list[TransactionSpec]:
        ...

    def detect_response(self, command: int, payload: bytes) -> str | None:
        ...

    def control_message(self, decoded: dict[str, Any]) -> str:
        ...

    def state_messages(self, state: ProtocolState, decoded: dict[str, Any]) -> Iterable[str]:
        ...

    def sensor_info_requests(self, decoded: dict[str, Any], already_requested: set[int]) -> Iterable[TransactionSpec]:
        ...
