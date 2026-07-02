from __future__ import annotations

import unittest

from airtouch4.payloads.common import parse_internal_temperature


class InternalTemperatureTests(unittest.TestCase):
    def test_internal_temperature_preserves_fractional_room_values(self) -> None:
        self.assertEqual(parse_internal_temperature(0x82), 24.0)
        self.assertEqual(parse_internal_temperature(0x86), 24.4)
        self.assertEqual(parse_internal_temperature(0x87), 24.5)

    def test_internal_temperature_handles_low_and_high_ranges(self) -> None:
        self.assertEqual(parse_internal_temperature(0x26), 13.0)
        self.assertEqual(parse_internal_temperature(0xE7), 34.0)
        self.assertIsNone(parse_internal_temperature(0xFF))


if __name__ == "__main__":
    unittest.main()
