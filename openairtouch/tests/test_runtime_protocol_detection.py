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
            FakeTransport([at4_response()]),
            RuntimeConfig(active=True, detect_seconds=0.01, init_transactions=False),
        )

        runtime.start()
        snapshot = runtime.snapshot()["runtime"]

        self.assertEqual(runtime.profile.name, "at4")
        self.assertEqual(snapshot["protocol"], "at4")
        self.assertEqual(snapshot["detected_protocol"], "at4")
        self.assertTrue(snapshot["protocol_latched"])
        self.assertTrue(snapshot["connected"])

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
