from __future__ import annotations

import unittest

from airtouch4.service.touchpad_temperature import resolve_touchpad_temperature


class TouchpadTemperatureResolverTests(unittest.TestCase):
    def test_adaptive_control_temperature_wins(self) -> None:
        result = resolve_touchpad_temperature(
            _runtime_state([{"temperature": 20.0, "power_name": "on"}]),
            {"indoor": {"state": {"temperature": 22.0}}},
            _adaptive_status(24.4),
            fallback=23.0,
        )

        self.assertEqual(result.temperature, 24.4)
        self.assertEqual(result.source, "adaptive_control")

    def test_home_assistant_indoor_wins_when_adaptive_not_controlling(self) -> None:
        result = resolve_touchpad_temperature(
            _runtime_state([{"temperature": 20.0, "power_name": "on"}]),
            {"indoor": {"state": {"temperature": 22.2}}},
            {"mode": "off"},
            fallback=23.0,
        )

        self.assertEqual(result.temperature, 22.2)
        self.assertEqual(result.source, "home_assistant_indoor")

    def test_averages_on_zones_before_all_zones(self) -> None:
        result = resolve_touchpad_temperature(
            _runtime_state([
                {"temperature": 20.0, "power_name": "on"},
                {"temperature": 28.0, "power_name": "off"},
                {"temperature": 22.0, "power_name": "turbo"},
            ]),
            {"indoor": {"state": {"temperature": None}}},
            {},
            fallback=23.0,
        )

        self.assertEqual(result.temperature, 21.0)
        self.assertEqual(result.source, "on_zone_average")
        self.assertEqual(result.detail["count"], 2)

    def test_averages_all_zones_when_no_zone_on(self) -> None:
        result = resolve_touchpad_temperature(
            _runtime_state([
                {"temperature": 20.0, "power_name": "off"},
                {"temperature": 22.0, "power_name": "off"},
            ]),
            {},
            {},
            fallback=23.0,
        )

        self.assertEqual(result.temperature, 21.0)
        self.assertEqual(result.source, "zone_average")

    def test_uses_configured_fallback(self) -> None:
        result = resolve_touchpad_temperature(_runtime_state([]), {}, {}, fallback=23.4)

        self.assertEqual(result.temperature, 23.4)
        self.assertEqual(result.source, "fallback")


def _runtime_state(groups: list[dict]) -> dict:
    return {
        "state": {
            "groups": {
                str(index): {"status": status}
                for index, status in enumerate(groups)
            }
        }
    }


def _adaptive_status(temperature: float) -> dict:
    return {
        "mode": "adaptive",
        "config": {"control_strategy": "hybrid"},
        "runtime_control": {"connected": True},
        "evaluations": [
            {
                "ac": 0,
                "hybrid": {
                    "strategy": "hybrid",
                    "control_temperature": temperature,
                },
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
