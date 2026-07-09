"""AirTouch 5 protocol detection adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ...packet import AirTouchPacket
from ...session.init import InitStep
from ...session.queue import TransactionSpec
from ...session.touchscreen import TouchscreenSession
from ...state import AirTouchState
from ..base import ProtocolCommandError, ProtocolState


@dataclass(frozen=True)
class AT5Profile:
    name: str = "at5"
    display_name: str = "AirTouch 5"

    def create_session(self, *, touchpad_temperature: float, heartbeat_interval: float) -> TouchscreenSession:
        return TouchscreenSession(
            touchpad_temperature=touchpad_temperature,
            heartbeat_interval=heartbeat_interval,
        )

    def create_state(self) -> AirTouchState:
        return AirTouchState()

    def decode_payload(self, command: int, payload: bytes) -> dict[str, Any]:
        return {
            "type": "unsupported_profile",
            "profile": self.name,
            "payload_len": len(payload),
        }

    def decode_packet(self, packet: AirTouchPacket) -> dict[str, Any]:
        return self.decode_payload(packet.command, packet.payload)

    def build_transaction(self, action: str, data: dict[str, Any], *, state: dict[str, Any] | None = None) -> TransactionSpec:
        raise ProtocolCommandError("commands are not supported for the detected protocol yet")

    def init_steps(self) -> list[InitStep]:
        return []

    def init_transactions(self) -> list[TransactionSpec]:
        return []

    def detect_response(self, command: int, payload: bytes) -> str | None:
        if command in {
            0xC021,
            0xC023,
            0xC027,
            0xC033,
            0xC045,
            0xC073,
        }:
            return self.name
        return None

    def control_message(self, decoded: dict[str, Any]) -> str:
        return ""

    def state_messages(self, state: ProtocolState, decoded: dict[str, Any]) -> Iterable[str]:
        return []

    def sensor_info_requests(self, decoded: dict[str, Any], already_requested: set[int]) -> Iterable[TransactionSpec]:
        return []


PROFILE = AT5Profile()
