"""Runtime loop for the OpenAirTouch replacement-touchscreen host."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable, Protocol

from ..packet import AirTouchPacket
from ..protocols import AT4, ProtocolProfile, ProtocolSession, ProtocolState, get_profile
from ..session.queue import TransactionEvent, TransactionQueue, TransactionSpec


class TransportLike(Protocol):
    """Minimal bus transport required by the runtime."""

    def read(self, size: int = 512) -> bytes:
        ...

    def write(self, data: bytes | bytearray | Iterable[int]) -> int:
        ...


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration for a live OpenAirTouch touchscreen host session."""

    active: bool = True
    detect_seconds: float = 3.0
    heartbeat_interval: float = 30.0
    touchpad_temperature: float = 23.0
    init_transactions: bool = True


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
    """Stateful protocol runtime for replacing the OpenAirTouch touchscreen.

    This class is the boundary between the packet/parser layer and application
    surfaces such as a terminal dashboard, HTTP API, or Home Assistant ingress
    UI. It owns the fresh-boot init flow, heartbeat, transaction queue, and
    state model.
    """

    transport: TransportLike
    config: RuntimeConfig = field(default_factory=RuntimeConfig)
    session: ProtocolSession | None = None
    transactions: TransactionQueue | None = None
    profile: ProtocolProfile | None = None
    state: ProtocolState | None = None
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
            self.profile = get_profile("auto")
        if self.session is None:
            self.session = self._profile.create_session(
                touchpad_temperature=self.config.touchpad_temperature,
                heartbeat_interval=self.config.heartbeat_interval,
            )
        if self.state is None:
            self.state = self._profile.create_state()
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
                "protocol_mode": "auto",
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
                "rx_count": self.rx_count,
                "tx_count": self.tx_count,
                "uptime_seconds": int(time.monotonic() - self.started_monotonic),
            },
            "transactions": transactions,
            "state": self._state.snapshot(),
        }

    @property
    def _session(self) -> ProtocolSession:
        if self.session is None:
            raise RuntimeError("runtime session is not initialised")
        return self.session

    @property
    def _state(self) -> ProtocolState:
        if self.state is None:
            raise RuntimeError("runtime state is not initialised")
        return self.state

    def _read_available(self) -> list[RuntimeEvent]:
        data = self.transport.read()
        if not data:
            return []
        events: list[RuntimeEvent] = []
        for packet in self._session.feed_rx(data):
            self.rx_count += 1
            detected = self._profile.detect_response(packet.command, packet.payload)
            decoded = self._profile.decode_packet(packet)
            if detected is not None:
                decoded = {**decoded, "detected_protocol": detected}
                self._handle_detected_protocol(detected)
            state_changed = decoded.get("decoder") != "client_api"
            message = self._state_log_message(decoded) if state_changed else ""
            if state_changed:
                self._state.apply_decoded(packet.command, decoded)
                self._state.last_command = packet.command
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
        message = self._profile.control_message(decoded)
        self._state.apply_decoded(packet.command, decoded)
        return RuntimeEvent("tx", packet=packet, wire=wire, message=message, decoded=decoded, state_changed=True)

    def _state_log_message(self, decoded: dict) -> str:
        return "; ".join(self._profile.state_messages(self._state, decoded))

    def _assign_address(self) -> int | None:
        return self._session.choose_available_address()

    @property
    def _profile(self) -> ProtocolProfile:
        return self.profile or AT4

    def _handle_detected_protocol(self, detected: str) -> None:
        self.detected_protocol = detected
        if detected == self._profile.name:
            self.protocol_mismatch = False
            return
        if detected != self._profile.name:
            self.protocol_mismatch = True
            self.boot_complete = False
            if self.transactions is not None:
                self.transactions = None

    def _queue_sensor_info_requests(self, decoded: dict) -> None:
        specs = list(self._profile.sensor_info_requests(decoded, self.sensor_info_requested))
        if specs:
            self.enqueue(specs)
