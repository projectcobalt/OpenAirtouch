from __future__ import annotations

import unittest

from airtouch4.payloads.common import (
    decode_touchpad_heartbeat_payload,
    encode_internal_temperature,
    encode_touchpad_heartbeat_payload,
    parse_internal_temperature,
)
from airtouch4.payloads.internal_status import decode_touchpad_temperature
from airtouch4.payloads.ui_config import decode_main_display_new


class InternalTemperatureTests(unittest.TestCase):
    def test_internal_temperature_preserves_tenths_precision(self) -> None:
        self.assertEqual(parse_internal_temperature(0x73), 22.5)
        self.assertEqual(parse_internal_temperature(0x79), 23.1)
        self.assertEqual(parse_internal_temperature(0x82), 24.0)

    def test_internal_temperature_handles_low_and_high_ranges(self) -> None:
        self.assertEqual(parse_internal_temperature(0x26), 13.0)
        self.assertEqual(parse_internal_temperature(0xE7), 34.0)
        self.assertIsNone(parse_internal_temperature(0xFF))

    def test_internal_temperature_encoder_uses_matching_offset(self) -> None:
        self.assertEqual(encode_internal_temperature(22), 0x6E)
        self.assertEqual(encode_internal_temperature(24), 0x82)

    def test_touchpad_heartbeat_uses_apk_short_payload(self) -> None:
        payload = encode_touchpad_heartbeat_payload(25.0)

        self.assertEqual(payload.hex(" ").upper(), "00 DC 00")
        self.assertEqual(decode_touchpad_heartbeat_payload(payload)["heartbeat_raw"], 220)
        self.assertEqual(decode_touchpad_heartbeat_payload(payload)["temperature"], 25.0)

    def test_touchpad_heartbeat_decoder_does_not_treat_low_byte_as_bus_temperature(self) -> None:
        decoded = decode_touchpad_temperature(bytes.fromhex("00 DC 00"))

        self.assertEqual(decoded["payload_encoding"], "apk_touchpad_short_le")
        self.assertEqual(decoded["heartbeat_raw"], 220)
        self.assertEqual(decoded["temperature"], 25.0)

    def test_main_display_new_uses_apk_sign_record_layout(self) -> None:
        decoded = decode_main_display_new(bytes.fromhex(
            "80 00 00 00 60 00 E1 00 01 00 80 00 02 00 80 00 03 00 80 00"
        ))

        self.assertEqual(decoded["active_favourite"], 0x80)
        self.assertEqual(decoded["record_count"], 4)
        self.assertEqual(decoded["records"][0]["ac"], 0)
        self.assertEqual(decoded["records"][0]["sign_sensor"], 0xE1)
        self.assertEqual(decoded["records"][0]["sign_group"], 1)
        self.assertEqual(decoded["records"][0]["sign_group_ui_zone"], 2)


if __name__ == "__main__":
    unittest.main()
