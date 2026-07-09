from __future__ import annotations

import unittest

from openairtouch.protocols.at5.packet import AT5DataPack, extract_datapacks, parse_datapack
from openairtouch.protocols.at5.profile import PROFILE
from openairtouch.protocols.at5.session import AT5Session


class AT5ProtocolTests(unittest.TestCase):
    def test_expanded_command_round_trips_as_sixteen_bit_command(self) -> None:
        packet = AT5DataPack(
            dest=0x80,
            src=0x90,
            packet_id=1,
            command=0xC021,
            payload=b"\x02\x00",
            repeat_records=(bytes.fromhex("00 03 FF 00"), bytes.fromhex("01 80 32 00")),
        )

        parsed = parse_datapack(packet.encode(stuff_raw=True))

        self.assertEqual(parsed.command, 0xC021)
        self.assertEqual(parsed.payload, b"\x02\x00")
        self.assertEqual(parsed.repeat_records, packet.repeat_records)
        self.assertTrue(parsed.crc_ok)

    def test_extractor_handles_apk_raw_mode_stuffing(self) -> None:
        packet = AT5DataPack(
            dest=0x80,
            src=0x90,
            packet_id=2,
            command=0xC023,
            payload=b"\x55\x55\x55",
        )

        wire = packet.encode(stuff_raw=True)
        packets = extract_datapacks(wire)

        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0].command, 0xC023)
        self.assertEqual(packets[0].payload, b"\x55\x55\x55")

    def test_session_builds_apk_query_extension_prelude(self) -> None:
        session = AT5Session(src=0x90)

        packet, wire = session.build_touchpad_info_request()

        self.assertEqual(packet.dest, 0x81)
        self.assertEqual(packet.command, 0x61)
        self.assertEqual(parse_datapack(wire).command, 0x61)

    def test_profile_uses_apk_initialisation_commands(self) -> None:
        specs = PROFILE.init_transactions()

        self.assertEqual(specs[0].command, 0xC045)
        self.assertEqual(specs[0].expected_commands, (0xC045,))
        self.assertIn(0xC021, {spec.command for spec in specs})
        self.assertIn(0xC05D, {spec.command for spec in specs})
        self.assertEqual(PROFILE.detect_response(0xC021, b""), "at5")


if __name__ == "__main__":
    unittest.main()
