from __future__ import annotations

import unittest

from airtouch4.session.touchscreen import TouchscreenSession


class TouchscreenSessionTests(unittest.TestCase):
    def test_heartbeat_uses_source_address_for_identity_and_payload_for_temperature(self) -> None:
        session = TouchscreenSession(src=0x91, touchpad_temperature=25.0)

        packet, _wire = session.build_heartbeat()

        self.assertEqual(packet.src, 0x91)
        self.assertEqual(packet.command, 0x26)
        self.assertEqual(packet.payload.hex(" ").upper(), "00 DC 00")

    def test_auto_address_chooses_unused_touchpad_slot(self) -> None:
        session = TouchscreenSession()
        session.seen_touchpad_addresses.add(1)

        selected = session.choose_available_address()

        self.assertEqual(selected, 0x91)
        self.assertEqual(session.source_slot(), 2)

    def test_raw_heartbeat_override_is_explicit(self) -> None:
        session = TouchscreenSession(src=0x91, heartbeat_payload=bytes.fromhex("00 91 00"), touchpad_temperature=25.0)

        packet, _wire = session.build_heartbeat()

        self.assertEqual(packet.payload.hex(" ").upper(), "00 91 00")

        session.set_touchpad_temperature(25.0)
        packet, _wire = session.build_heartbeat()

        self.assertEqual(packet.payload.hex(" ").upper(), "00 DC 00")


if __name__ == "__main__":
    unittest.main()
