"""AirTouch 5 protocol adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ...session.init import InitStep
from ...session.queue import TransactionSpec
from ...state import AirTouchState
from ..base import ProtocolCommandError, ProtocolPacket, ProtocolState
from .packet import AT5DataPack, command_name
from .session import AT5Session, AT5_INIT_COMMANDS

AT5_RESPONSE_COMMANDS = {
    0x001B,
    0x0061,
    0x0091,
    0xC021,
    0xC023,
    0xC027,
    0xC02B,
    0xC02F,
    0xC033,
    0xC043,
    0xC045,
    0xC047,
    0xC051,
    0xC055,
    0xC057,
    0xC059,
    0xC05B,
    0xC05D,
    0xC05F,
    0xC071,
    0xC073,
}


@dataclass(frozen=True)
class AT5Profile:
    name: str = "at5"
    display_name: str = "AirTouch 5"

    def create_session(self, *, touchpad_temperature: float, heartbeat_interval: float) -> AT5Session:
        return AT5Session(
            touchpad_temperature=touchpad_temperature,
            heartbeat_interval=heartbeat_interval,
        )

    def create_state(self) -> AirTouchState:
        return AirTouchState()

    def decode_payload(self, command: int, payload: bytes) -> dict[str, Any]:
        return {
            "type": "at5_packet",
            "profile": self.name,
            "command": command,
            "command_name": command_name(command),
            "payload_len": len(payload),
        }

    def decode_packet(self, packet: ProtocolPacket) -> dict[str, Any]:
        decoded = self.decode_payload(packet.command, packet.payload)
        if isinstance(packet, AT5DataPack):
            decoded = {
                **decoded,
                "repeat_count": len(packet.repeat_records),
                "repeat_lengths": [len(record) for record in packet.repeat_records],
            }
        return decoded

    def build_transaction(self, action: str, data: dict[str, Any], *, state: dict[str, Any] | None = None) -> TransactionSpec:
        raise ProtocolCommandError("commands are not supported for the detected protocol yet")

    def init_steps(self) -> list[InitStep]:
        return []

    def init_transactions(self) -> list[TransactionSpec]:
        return [
            TransactionSpec(
                command=command,
                payload=payload,
                expected_commands=(command,),
                name=f"at5 {name}",
                max_attempts=3,
                timeout=2.0,
                require_match=True,
                block_on_failure=True,
            )
            for command, payload, name in AT5_INIT_COMMANDS
        ]

    def detect_response(self, command: int, payload: bytes) -> str | None:
        if command in AT5_RESPONSE_COMMANDS:
            return self.name
        return None

    def control_message(self, decoded: dict[str, Any]) -> str:
        return ""

    def state_messages(self, state: ProtocolState, decoded: dict[str, Any]) -> Iterable[str]:
        return []

    def sensor_info_requests(self, decoded: dict[str, Any], already_requested: set[int]) -> Iterable[TransactionSpec]:
        return []


PROFILE = AT5Profile()
