from __future__ import annotations

from collections import deque
from typing import Iterable
import unittest

from openairtouch.packet import AirTouchPacket
from openairtouch.protocols.at5.packet import AT5DataPack
from openairtouch.runtime import AirTouchRuntime, RuntimeConfig


class FakeTransport:
    def __init__(self, reads: Iterable[bytes] = ()) -> None:
        self.reads = deque(reads)
        self.writes: list[bytes] = []

    def read(self, size: int = 512) -> bytes:
        if self.reads:
            return self.reads.popleft()
        return b""

    def write(self, data: bytes | bytearray | Iterable[int]) -> int:
        wire = bytes(data)
        self.writes.append(wire)
        return len(wire)


def at4_response(command: int = 0x55) -> bytes:
    return AirTouchPacket(
        dest=0x90,
        src=0x80,
        packet_id=1,
        command=command,
        payload=b"",
        raw_mode=True,
    ).encode(stuff_raw=True)


def touchpad_presence(slot: int) -> bytes:
    payload = bytearray(21)
    payload[0] = 0xFF
    payload[1] = 0x01
    payload[10] = 0x40 | slot
    payload[20] = 0
    return AirTouchPacket(
        dest=0x9F,
        src=0x90 if slot == 1 else 0x91,
        packet_id=slot,
        command=0x1F,
        payload=bytes(payload),
        raw_mode=True,
    ).encode(stuff_raw=True)


def at5_response(command: int = 0xC045) -> bytes:
    return AT5DataPack(
        dest=0x90,
        src=0x80,
        packet_id=1,
        command=command,
        payload=b"\x01",
    ).encode(stuff_raw=True)


class RuntimeProtocolDetectionTests(unittest.TestCase):
    def test_auto_detection_latches_at5_for_runtime_lifetime(self) -> None:
        transport = FakeTransport([at5_response()])
        runtime = AirTouchRuntime(
            transport,
            RuntimeConfig(active=True, detect_seconds=0.01, init_transactions=True),
        )

        events = runtime.start()
        snapshot = runtime.snapshot()["runtime"]

        self.assertEqual(runtime.profile.name, "at5")
        self.assertEqual(snapshot["protocol"], "at5")
        self.assertEqual(snapshot["detected_protocol"], "at5")
        self.assertTrue(snapshot["protocol_latched"])
        self.assertTrue(snapshot["connected"])
        self.assertTrue(any(event.event == "rx" and event.packet and event.packet.command == 0xC045 for event in events))
        self.assertGreaterEqual(len(transport.writes), 4)

    def test_auto_detection_latches_at4_for_runtime_lifetime(self) -> None:
        runtime = AirTouchRuntime(
            FakeTransport([at4_response(), touchpad_presence(1)]),
            RuntimeConfig(active=True, detect_seconds=0.01, init_transactions=False),
        )

        runtime.start()
        snapshot = runtime.snapshot()["runtime"]

        self.assertEqual(runtime.profile.name, "at4")
        self.assertEqual(snapshot["protocol"], "at4")
        self.assertEqual(snapshot["detected_protocol"], "at4")
        self.assertTrue(snapshot["protocol_latched"])
        self.assertTrue(snapshot["connected"])
        self.assertEqual(snapshot["src"], "0x91")

    def test_auto_detection_fails_closed_without_address_evidence(self) -> None:
        runtime = AirTouchRuntime(
            FakeTransport([at4_response()]),
            RuntimeConfig(active=True, detect_seconds=0.01, init_transactions=False),
        )

        events = runtime.start()
        snapshot = runtime.snapshot()["runtime"]

        self.assertEqual(snapshot["protocol"], "at4")
        self.assertFalse(snapshot["connected"])
        self.assertTrue(snapshot["protocol_latched"])
        self.assertFalse(snapshot["address_assigned"])
        self.assertTrue(any("no free touchpad address" in event.message for event in events))

    def test_auto_detection_can_explicitly_share_secondary_address(self) -> None:
        runtime = AirTouchRuntime(
            FakeTransport([at4_response(), touchpad_presence(1), touchpad_presence(2)]),
            RuntimeConfig(
                active=True,
                detect_seconds=0.01,
                init_transactions=False,
                allow_shared_secondary_address=True,
            ),
        )

        runtime.start()
        snapshot = runtime.snapshot()["runtime"]

        self.assertTrue(snapshot["connected"])
        self.assertEqual(snapshot["src"], "0x91")
        self.assertTrue(snapshot["allow_shared_secondary_address"])

    def test_auto_detection_fails_closed_without_supported_response(self) -> None:
        runtime = AirTouchRuntime(
            FakeTransport(),
            RuntimeConfig(active=True, detect_seconds=0.01, init_transactions=True),
        )

        events = runtime.start()
        snapshot = runtime.snapshot()["runtime"]

        self.assertFalse(snapshot["connected"])
        self.assertFalse(snapshot["boot_complete"])
        self.assertFalse(snapshot["protocol_latched"])
        self.assertTrue(snapshot["protocol_detection_failed"])
        self.assertIsNone(runtime.transactions)
        self.assertTrue(any("no supported AirTouch protocol detected" in event.message for event in events))


if __name__ == "__main__":
    unittest.main()
