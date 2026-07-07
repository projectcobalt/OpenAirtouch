"""Runtime loop for the AirTouch replacement-touchscreen host."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable, Protocol

from ..constants import ADDR_TOUCHPAD_1
from ..packet import AirTouchPacket
from ..payloads import decode_packet_payload
from ..profiles import AT4, ProtocolProfile, get_profile
from ..session.queue import TransactionEvent, TransactionQueue, TransactionSpec
from ..session.touchscreen import TouchscreenSession
from ..state import AirTouchState


class TransportLike(Protocol):
    """Minimal bus transport required by the runtime."""

    def read(self, size: int = 512) -> bytes:
        ...

    def write(self, data: bytes | bytearray | Iterable[int]) -> int:
        ...


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration for a live AirTouch touchscreen host session."""

    active: bool = True
    detect_seconds: float = 3.0
    heartbeat_interval: float = 30.0
    heartbeat_payload: bytes | None = None
    touchpad_temperature: float = 23.0
    source_address: int | None = None
    auto_address: bool = True
    force_source_address: bool = False
    init_transactions: bool = True
    protocol: str = "auto"


@dataclass(frozen=True)
class RuntimeEvent:
    """Event emitted by the runtime loop."""

    event: str
    packet: AirTouchPacket | None = None
    wire: bytes | None = None
    transaction: TransactionEvent | None = None
    message: str = ""
    decoded: dict | None = None
    state_changed: bool = False

    @property
    def direction(self) -> str | None:
        if self.event in {"rx", "tx"}:
            return self.event
        return None


@dataclass
class AirTouchRuntime:
    """Stateful protocol runtime for replacing the AirTouch touchscreen.

    This class is the boundary between the packet/parser layer and application
    surfaces such as a terminal dashboard, HTTP API, or Home Assistant ingress
    UI. It owns the fresh-boot init flow, heartbeat, transaction queue, and
    state model.
    """

    transport: TransportLike
    config: RuntimeConfig = field(default_factory=RuntimeConfig)
    session: TouchscreenSession | None = None
    transactions: TransactionQueue | None = None
    profile: ProtocolProfile | None = None
    state: AirTouchState = field(default_factory=AirTouchState)
    rx_count: int = 0
    tx_count: int = 0
    started_monotonic: float = field(default_factory=time.monotonic)
    boot_complete: bool = False
    address_assigned: bool = False
    detected_protocol: str | None = None
    protocol_mismatch: bool = False
    sensor_info_requested: set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.profile is None:
            self.profile = get_profile(self.config.protocol)
        if self.session is None:
            self.session = TouchscreenSession(
                src=self.config.source_address or ADDR_TOUCHPAD_1,
                heartbeat_payload=self.config.heartbeat_payload,
                touchpad_temperature=self.config.touchpad_temperature,
                heartbeat_interval=self.config.heartbeat_interval,
                auto_address=False,
            )
        if self.transactions is None and self.config.active and self.config.init_transactions:
            self.transactions = TransactionQueue()
            self.transactions.enqueue_many(self._profile.init_transactions())

    def enqueue(self, specs: Iterable[TransactionSpec]) -> None:
        if self.transactions is None:
            self.transactions = TransactionQueue()
        self.transactions.enqueue_many(tuple(specs))

    def set_touchpad_temperature(self, temperature: float, *, source: str = "runtime", detail: dict | None = None) -> None:
        self._session.set_touchpad_temperature(temperature, source=source, detail=detail)

    def start(self, *, now: float | None = None) -> list[RuntimeEvent]:
        """Run the active-mode address-detection prelude."""
        if not self.config.active:
            self.boot_complete = True
            return [RuntimeEvent("status", message="passive runtime started")]

        current = time.monotonic() if now is None else now
        events: list[RuntimeEvent] = []
        packet, wire = self._session.build_touchpad_info_request()
        events.append(self._tx_event(packet, wire))

        detect_until = current + self.config.detect_seconds
        while time.monotonic() < detect_until:
            events.extend(self._read_available())

        address = self._assign_address()
        if address is None:
            occupied = ", ".join(f"0x{address:02X}" for address in self._session.occupied_touchpad_addresses()) or "none"
            self.boot_complete = False
            self.address_assigned = False
            events.append(RuntimeEvent(
                "status",
                message=f"no free touchpad address; occupied: {occupied}; runtime held before init",
            ))
            return events

        self.boot_complete = True
        self.address_assigned = True
        events.append(RuntimeEvent("status", message=f"using touchpad address 0x{address:02X}"))
        return events

    def step(self, *, now: float | None = None) -> list[RuntimeEvent]:
        """Process one runtime tick and return all resulting events."""
        current = time.monotonic() if now is None else now
        events = self._read_available()
        if not self.config.active or not self.address_assigned:
            return events

        if self._session.due_heartbeat(current):
            packet, wire = self._session.build_heartbeat()
            events.append(self._tx_event(packet, wire))
            self._session.mark_heartbeat_sent(current)

        if self.transactions is not None:
            transaction_events, request = self.transactions.poll(current)
            events.extend(RuntimeEvent("transaction", transaction=event) for event in transaction_events)
            if request is not None:
                packet, wire = self._session.build_packet(request.command, request.payload)
                events.append(self._tx_event(packet, wire))

        return events

    def run(self, *, duration: float | None = None) -> Iterable[RuntimeEvent]:
        """Yield runtime events until stopped or the optional duration expires."""
        started = time.monotonic()
        yield from self.start(now=started)
        while True:
            now = time.monotonic()
            if duration is not None and now - started >= duration:
                yield RuntimeEvent("status", message="duration_exit")
                return
            yield from self.step(now=now)

    def snapshot(self) -> dict:
        transactions = None if self.transactions is None else self.transactions.summary()
        connected = (
            self.config.active
            and self.boot_complete
            and self.address_assigned
            and not self.protocol_mismatch
        )
        return {
            "runtime": {
                "active": self.config.active,
                "connected": connected,
                "protocol_mode": self.config.protocol,
                "protocol": self._profile.name,
                "protocol_name": self._profile.display_name,
                "detected_protocol": self.detected_protocol,
                "protocol_mismatch": self.protocol_mismatch,
                "boot_complete": self.boot_complete,
                "address_assigned": self.address_assigned,
                "src": f"0x{self._session.src:02X}",
                "dest": f"0x{self._session.dest:02X}",
                "touchpad_temperature": self._session.touchpad_temperature,
                "touchpad_temperature_source": self._session.touchpad_temperature_source,
                "touchpad_temperature_detail": self._session.touchpad_temperature_detail,
                "heartbeat_payload": self._session.current_heartbeat_payload().hex(" ").upper(),
                "heartbeat_payload_override": self._session.heartbeat_payload is not None,
                "rx_count": self.rx_count,
                "tx_count": self.tx_count,
                "uptime_seconds": int(time.monotonic() - self.started_monotonic),
            },
            "transactions": transactions,
            "state": self.state.snapshot(),
        }

    @property
    def _session(self) -> TouchscreenSession:
        if self.session is None:
            raise RuntimeError("runtime session is not initialised")
        return self.session

    def _read_available(self) -> list[RuntimeEvent]:
        data = self.transport.read()
        if not data:
            return []
        events: list[RuntimeEvent] = []
        for packet in self._session.feed_rx(data):
            self.rx_count += 1
            detected = self._profile.detect_response(packet.command, packet.payload)
            decoded = decode_packet_payload(packet, self._profile.decode_payload)
            if detected is not None:
                decoded = {**decoded, "detected_protocol": detected}
                self._handle_detected_protocol(detected)
            state_changed = decoded.get("decoder") != "client_api"
            message = self._state_log_message(decoded) if state_changed else ""
            if state_changed:
                self.state.apply_decoded(packet.command, decoded)
                self.state.last_command = packet.command
                self._queue_sensor_info_requests(decoded)
            events.append(RuntimeEvent("rx", packet=packet, message=message, decoded=decoded, state_changed=state_changed))
            if self.transactions is not None:
                events.extend(
                    RuntimeEvent("transaction", transaction=event)
                    for event in self.transactions.observe(packet)
                )
        return events

    def _write(self, wire: bytes) -> None:
        self.transport.write(wire)
        self.tx_count += 1

    def _tx_event(self, packet: AirTouchPacket, wire: bytes) -> RuntimeEvent:
        self._write(wire)
        decoded = self._profile.decode_payload(packet.command, packet.payload)
        message = _control_log_message(decoded)
        self.state.apply_decoded(packet.command, decoded)
        return RuntimeEvent("tx", packet=packet, wire=wire, message=message, decoded=decoded, state_changed=True)

    def _state_log_message(self, decoded: dict) -> str:
        messages: list[str] = []
        kind = decoded.get("type")
        if kind == "ac_status_internal":
            for record in decoded.get("records", []):
                if isinstance(record, dict):
                    messages.extend(_ac_status_change_messages(self.state, record))
        elif kind == "group_status_internal":
            for record in decoded.get("records", []):
                if isinstance(record, dict):
                    messages.extend(_group_status_change_messages(self.state, record))
        return "; ".join(messages)

    def _assign_address(self) -> int | None:
        if self.config.force_source_address and self.config.source_address is not None:
            return self._session.choose_available_address(
                self.config.source_address,
                allow_occupied=True,
            )
        if not self.config.auto_address and self.config.source_address is not None:
            return self._session.choose_available_address(
                self.config.source_address,
                allow_occupied=False,
            )
        return self._session.choose_available_address(self.config.source_address)

    @property
    def _profile(self) -> ProtocolProfile:
        return self.profile or AT4

    def _handle_detected_protocol(self, detected: str) -> None:
        self.detected_protocol = detected
        configured = self.config.protocol.lower()
        if detected == self._profile.name and configured in {"auto", detected}:
            self.protocol_mismatch = False
            return
        if detected != self._profile.name or configured not in {"auto", detected}:
            self.protocol_mismatch = True
            self.boot_complete = False
            if self.transactions is not None:
                self.transactions = None

    def _queue_sensor_info_requests(self, decoded: dict) -> None:
        if decoded.get("type") != "sensor_list":
            return
        addresses = decoded.get("sensor_addresses") or []
        specs = []
        for sensor in addresses:
            if not isinstance(sensor, int) or sensor in self.sensor_info_requested:
                continue
            self.sensor_info_requested.add(sensor)
            specs.append(TransactionSpec(
                0x73,
                bytes((sensor,)),
                expected_commands=(0x73,),
                name=f"sensor info 0x{sensor:02X}" if sensor >= 0x80 else f"sensor info {sensor}",
                max_attempts=2,
                timeout=2.0,
            ))
        if specs:
            self.enqueue(specs)


def _control_log_message(decoded: dict) -> str:
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
