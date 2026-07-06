from __future__ import annotations

import unittest

from airtouch4.service.commands import build_transaction


class ServiceCommandTests(unittest.TestCase):
    def test_ac_mode_intent_carries_current_setpoint_like_airtouch_app(self) -> None:
        state = {
            "acs": {
                "0": {
                    "status": {
                        "mode": 4,
                        "fan": 0,
                        "setpoint": 21,
                    },
                    "settings": {
                        "min_setpoint": 16,
                        "max_setpoint": 30,
                    },
                },
            },
        }

        spec = build_transaction("ac_status", {"ac": 0, "mode": 1}, state=state)

        self.assertEqual(spec.command, 0x22)
        self.assertEqual(spec.payload.hex(" ").upper(), "00 10 11 00")

    def test_ac_mode_intent_uses_current_ac_setpoint_even_in_fan_mode(self) -> None:
        state = {
            "acs": {
                "0": {
                    "status": {
                        "mode": 3,
                        "fan": 1,
                        "setpoint": 24,
                    },
                    "settings": {
                        "min_setpoint": 16,
                        "max_setpoint": 30,
                    },
                },
            },
        }

        spec = build_transaction("ac_status", {"ac": 0, "mode": 1}, state=state)

        self.assertEqual(spec.command, 0x22)
        self.assertEqual(spec.payload.hex(" ").upper(), "00 11 14 00")

    def test_ac_mode_intent_without_state_uses_protocol_sentinel(self) -> None:
        spec = build_transaction("ac_status", {"ac": 0, "mode": 1})

        self.assertEqual(spec.command, 0x22)
        self.assertEqual(spec.payload.hex(" ").upper(), "00 17 1F 00")


if __name__ == "__main__":
    unittest.main()
