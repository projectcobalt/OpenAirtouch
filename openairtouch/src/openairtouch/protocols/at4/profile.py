"""AirTouch 4 protocol adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ...packet import AirTouchPacket
from ...payloads import decode_packet_payload
from ...payloads.registry import decode_mainboard_payload
from ...session.init import InitStep, default_init_steps
from ...session.queue import TransactionSpec
from ...session.touchscreen import TouchscreenSession
from ...state import AirTouchState
from ..base import ProtocolState
from .commands import build_transaction


@dataclass(frozen=True)
class AT4Profile:
    name: str = "at4"
    display_name: str = "AirTouch 4"

    def create_session(self, *, touchpad_temperature: float, heartbeat_interval: float) -> TouchscreenSession:
        return TouchscreenSession(
            touchpad_temperature=touchpad_temperature,
            heartbeat_interval=heartbeat_interval,
        )

    def create_state(self) -> AirTouchState:
        return AirTouchState()

    def decode_payload(self, command: int, payload: bytes) -> dict[str, Any]:
        return decode_mainboard_payload(command, payload)

    def decode_packet(self, packet: AirTouchPacket) -> dict[str, Any]:
        return decode_packet_payload(packet, self.decode_payload)

    def build_transaction(self, action: str, data: dict[str, Any], *, state: dict[str, Any] | None = None) -> TransactionSpec:
        return build_transaction(action, data, state=state)

    def init_steps(self) -> list[InitStep]:
        return default_init_steps()

    def init_transactions(self) -> list[TransactionSpec]:
        return [
            TransactionSpec(
                command=step.command,
                payload=step.payload,
                expected_commands=(step.command,),
                name=step.name,
                max_attempts=step.max_attempts,
                timeout=step.retry_interval,
                require_match=True,
                block_on_failure=step.required,
            )
            for step in self.init_steps()
        ]

    def detect_response(self, command: int, payload: bytes) -> str | None:
        if command == 0x55:
            return self.name
        return None

    def control_message(self, decoded: dict[str, Any]) -> str:
        kind = decoded.get("type")
        if kind == "set_ac_status_internal":
            parts = [f"[C]AC({_text(decoded.get('ac'))}) SET"]
            power = decoded.get("power_name")
            if power and power != "unchanged":
                parts.append(f"Power: {_power_text(power)}")
            if decoded.get("setpoint") is not None:
                parts.append(f"SetPoint: {decoded.get('setpoint')}")
            if decoded.get("mode") is not None:
                parts.append(f"Mode: {_mode_text(decoded.get('mode'))}")
            if decoded.get("fan") is not None:
                parts.append(f"Fan: {_text(decoded.get('fan'))}")
            return " ".join(parts) if len(parts) > 1 else ""
        if kind == "set_group_status_internal":
            parts = [f"[C]Group({_text(decoded.get('group'))}) SET"]
            power = decoded.get("power_name")
            if power and power != "value_change":
                parts.append(f"Power: {_power_text(power)}")
            if decoded.get("sensor_control"):
                parts.append(f"SetPoint: {_text(decoded.get('setpoint'))}")
            elif decoded.get("percentage") is not None:
                parts.append(f"Open: {_text(decoded.get('percentage'))}")
            return " ".join(parts) if len(parts) > 1 else ""
        if kind == "group_control_client":
            parts = [f"[C]Group({_text(decoded.get('group'))}) SET"]
            power = decoded.get("power_name")
            if power and power != "unchanged":
                parts.append(f"Power: {_power_text(power)}")
            setting = decoded.get("setting") if isinstance(decoded.get("setting"), dict) else {}
            if setting.get("setpoint") is not None:
                parts.append(f"SetPoint: {setting.get('setpoint')}")
            if setting.get("damper_percentage") is not None:
                parts.append(f"Open: {setting.get('damper_percentage')}")
            return " ".join(parts) if len(parts) > 1 else ""
        if kind == "ac_control_client":
            parts = [f"[C]AC({_text(decoded.get('ac'))}) SET"]
            power = decoded.get("power_name")
            if power and power != "unchanged":
                parts.append(f"Power: {_power_text(power)}")
            if decoded.get("setpoint") is not None:
                parts.append(f"SetPoint: {decoded.get('setpoint')}")
            if decoded.get("mode") is not None:
                parts.append(f"Mode: {_mode_text(decoded.get('mode'))}")
            if decoded.get("fan") is not None:
                parts.append(f"Fan: {_text(decoded.get('fan'))}")
            return " ".join(parts) if len(parts) > 1 else ""
        return ""

    def state_messages(self, state: ProtocolState, decoded: dict[str, Any]) -> Iterable[str]:
        if not isinstance(state, AirTouchState):
            return []
        messages: list[str] = []
        kind = decoded.get("type")
        if kind == "ac_status_internal":
            for record in decoded.get("records", []):
                if isinstance(record, dict):
                    messages.extend(_ac_status_change_messages(state, record))
        elif kind == "group_status_internal":
            for record in decoded.get("records", []):
                if isinstance(record, dict):
                    messages.extend(_group_status_change_messages(state, record))
        return messages

    def sensor_info_requests(self, decoded: dict[str, Any], already_requested: set[int]) -> Iterable[TransactionSpec]:
        if decoded.get("type") != "sensor_list":
            return []
        specs = []
        for sensor in decoded.get("sensor_addresses") or []:
            if not isinstance(sensor, int) or sensor in already_requested:
                continue
            already_requested.add(sensor)
            specs.append(TransactionSpec(
                0x73,
                bytes((sensor,)),
                expected_commands=(0x73,),
                name=f"sensor info 0x{sensor:02X}" if sensor >= 0x80 else f"sensor info {sensor}",
                max_attempts=2,
                timeout=2.0,
            ))
        return specs


def _ac_status_change_messages(state: AirTouchState, record: dict) -> list[str]:
    ac = record.get("ac")
    previous = state.acs.get(ac, {}).get("status", {}) if isinstance(ac, int) else {}
    messages = []
    messages.extend(_change_message(f"[M]AC({_text(ac)}) Power", previous.get("power_on"), record.get("power_on"), _on_off))
    messages.extend(_change_message(f"[M]AC({_text(ac)}) Mode", previous.get("mode"), record.get("mode"), _mode_text))
    messages.extend(_change_message(f"[M]AC({_text(ac)}) Fan", previous.get("fan"), record.get("fan"), _text))
    messages.extend(_change_message(f"[M]AC({_text(ac)}) SetPoint", previous.get("setpoint"), record.get("setpoint"), _text))
    messages.extend(_change_message(f"[M]AC({_text(ac)}) Error", previous.get("error_code"), record.get("error_code"), _text))
    return messages


def _group_status_change_messages(state: AirTouchState, record: dict) -> list[str]:
    group = record.get("group")
    previous = state.groups.get(group, {}).get("status", {}) if isinstance(group, int) else {}
    messages = []
    messages.extend(_change_message(f"[M]Group({_text(group)}) Power", previous.get("power_name"), record.get("power_name"), _power_text))
    messages.extend(_change_message(f"[M]Group({_text(group)}) Open", previous.get("percentage"), record.get("percentage"), _text))
    messages.extend(_change_message(f"[M]Group({_text(group)}) SetPoint", previous.get("setpoint"), record.get("setpoint"), _text))
    messages.extend(_change_message(f"[M]Group({_text(group)}) Temp", previous.get("temperature"), record.get("temperature"), _text))
    messages.extend(_change_message(f"[M]Group({_text(group)}) Spill", previous.get("spill_on"), record.get("spill_on"), _on_off))
    return messages


def _change_message(label: str, old: object, new: object, formatter) -> list[str]:
    if old is None or new is None or old == new:
        return []
    return [f"{label}: {formatter(old)}->{formatter(new)}"]


def _mode_text(value: object) -> str:
    names = {0: "Auto", 1: "Heat", 2: "Dry", 3: "Fan", 4: "Cool"}
    try:
        return names.get(int(value), str(value))
    except (TypeError, ValueError):
        return str(value)


def _power_text(value: object) -> str:
    text = str(value).replace("_", " ").strip()
    if text.lower() in {"on", "off", "turbo"}:
        return text.upper() if text.lower() in {"on", "off"} else "Turbo"
    return text[:1].upper() + text[1:]


def _on_off(value: object) -> str:
    return "ON" if bool(value) else "OFF"


def _text(value: object) -> str:
    return "-" if value is None else str(value)


PROFILE = AT4Profile()
