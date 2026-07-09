from __future__ import annotations

import unittest

from openairtouch.service.adaptive_contracts import AdaptiveCommandIntent, build_adaptive_input_contract, build_adaptive_ui_contract
from openairtouch.service.adaptive import AdaptiveConfig, AdaptiveController
from tests.test_adaptive import integrations, ready_heating_model, runtime_state, seed_learning_model


class AdaptiveContractTests(unittest.TestCase):
    def test_command_intent_keeps_protocol_request_neutral(self) -> None:
        intent = AdaptiveCommandIntent(
            intent="set_zone_damper",
            data={"group": 0, "percentage": 65},
            surface="zone",
            reason="hybrid damper plan",
            transaction_action="group_percentage",
            transaction_data={"group": 0, "percentage": 65},
            restore_key="group:0:percentage",
            expected_value=65,
        )

        self.assertEqual(intent.as_transaction_request(), {"action": "group_percentage", "data": {"group": 0, "percentage": 65}})
        self.assertEqual(intent.as_status()["intent"], "set_zone_damper")
        self.assertEqual(intent.as_status()["transaction"]["action"], "group_percentage")
        self.assertEqual(intent.as_status()["expected_value"], 65)
        self.assertEqual(intent.surface, "zone")
        self.assertEqual(intent.restore_key, "group:0:percentage")

    def test_input_contract_normalizes_runtime_and_integration_state(self) -> None:
        contract = build_adaptive_input_contract(
            {"state": {"acs": {"0": {"status": {"power_on": True}}}}},
            {
                "weather": {"state": {"temperature": 21.5}},
                "indoor": {"state": {"temperature": 22.0}},
                "forecast": {"state": {"daily": []}},
                "solar": {"state": {"q_solar": 0.0}},
                "ac_telemetry": {"state": {"compressor": "off"}},
            },
            {"connected": True, "reason": None},
        )

        self.assertTrue(contract.runtime_connected)
        self.assertIsNone(contract.runtime_reason)
        self.assertEqual(contract.airtouch_state["acs"]["0"]["status"]["power_on"], True)
        self.assertEqual(contract.weather["temperature"], 21.5)
        self.assertEqual(contract.indoor["temperature"], 22.0)
        self.assertEqual(contract.ac_telemetry["compressor"], "off")

    def test_ui_contract_surfaces_status_without_frontend_strategy_parsing(self) -> None:
        contract = build_adaptive_ui_contract(
            {
                "mode": "adaptive",
                "config": {"control_strategy": "hybrid"},
                "outside_temperature": 18.5,
                "forecast_quality": {"status": "ok", "used_for_control": True},
                "recommendations": ["Recommended Target: 22 C / Expected Runtime: 0.6 H"],
                "actions": ["Set Zone 1 To 100%"],
                "active_restore": [],
                "active_ac": [],
                "active_groups": [0],
                "active_dampers": [0],
                "solar": {"q_solar": 0.0},
                "ac_telemetry": {"source": "none"},
                "learning": {
                    "zones": {
                        "0": {
                            "mpc_ready": True,
                            "learn": True,
                            "accelerated_learning": True,
                            "learning_progress": 0.5,
                            "confidence": 0.7,
                            "passive_samples": 12,
                            "active_samples": 3,
                            "ekf_updates": 4,
                            "prediction_std": 0.2,
                            "passive_drift_per_hour": 0.1,
                            "active_response_per_hour": 0.6,
                            "outside_coupling_per_hour": 0.01,
                        }
                    },
                    "analytics": {"0": [{"temperature": 19.0}, {"temperature": 19.5}]},
                    "forecasts": {"0": [{"predicted_temperature": 20.0}, {"predicted_temperature": 21.0}]},
                },
                "intents": [
                    {
                        "ac": 0,
                        "headline": "Heating Expected",
                        "summary": "Recommended Target: 22 C / Expected Runtime: 0.6 H",
                        "intent": "heat",
                        "authority": "control",
                        "recommended_target": 22,
                        "runtime_hours": 0.6,
                    }
                ],
                "evaluations": [
                    {
                        "ac": 0,
                        "indoor_temperature": 19.0,
                        "indoor_source": "zone",
                        "mpc": {
                            "target": 22,
                            "action": "raise_setpoint",
                            "zone_power_fractions": {"0": 1.0},
                            "runtime_forecast": {
                                "runtime_hours": 0.6,
                                "series": [{"control_temperature": 19.0, "average_indoor_temperature": 19.0}],
                            },
                        },
                        "hybrid": {
                            "strategy": "hybrid",
                            "control_temperature": 19,
                            "damper_percentages": {"0": 100},
                            "touchpad_sensor": 0x91,
                        },
                    }
                ],
            }
        )

        self.assertEqual(contract["version"], 1)
        self.assertEqual(contract["summary"]["headline"], "Heating Expected")
        self.assertEqual(contract["surfaces"]["environment"]["fields"][0]["raw"], 18.5)
        self.assertEqual(contract["surfaces"]["zone"]["fields"][0]["label"], "Target")
        self.assertEqual(contract["surfaces"]["hybrid"]["fields"][0]["label"], "Control Temperature")
        self.assertEqual(contract["metrics"][0]["label"], "Authority")
        self.assertEqual(contract["metrics"][0]["value"], "Control")
        self.assertEqual(contract["metrics"][2]["label"], "Control Temperature")
        self.assertEqual(contract["metrics"][2]["raw"], 19.0)
        self.assertEqual(contract["metrics"][3]["value"], "2 active changes")
        self.assertEqual(contract["analytics"]["cards"][0]["id"], 0)
        self.assertEqual(contract["analytics"]["cards"][0]["state"], "Ready")
        self.assertEqual(contract["analytics"]["cards"][0]["flags"], ["Control", "Damper", "Ready", "Learning"])
        self.assertEqual(contract["analytics"]["cards"][0]["badges"][0]["value"], "50%")
        self.assertEqual(contract["analytics"]["cards"][0]["badges"][1]["value"], "12/3")
        self.assertEqual(contract["analytics"]["cards"][0]["chart"]["variant"], "hybrid")
        self.assertEqual(contract["analytics"]["cards"][0]["chart"]["title"], "Hybrid Plan")
        self.assertTrue(contract["analytics"]["cards"][0]["chart"]["has_data"])
        self.assertEqual(contract["analytics"]["cards"][0]["chart"]["lines"][0]["key"], "room")
        self.assertEqual(contract["plan"]["target"], 22.0)
        self.assertEqual(contract["plan"]["control_temperature"], 19.0)
        self.assertEqual(contract["plan"]["damper_percentages"], {"0": 100})

    def test_controller_status_includes_zone_ui_contract(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(mode="adaptive", control_strategy="zone", command_cooldown=1, control_zones=(0,))
        )
        seed_learning_model(controller, 0, ready_heating_model())

        controller.evaluate(
            runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=19),
            integrations(30),
            now=1.0,
        )

        ui = controller.status()["ui"]
        self.assertEqual(ui["summary"]["headline"], "Heating Expected")
        self.assertEqual(ui["surfaces"]["zone"]["fields"][0]["label"], "Target")
        self.assertEqual(ui["metrics"][2]["label"], "Control Temperature")
        self.assertEqual(ui["analytics"]["cards"][0]["state"], "Ready")
        self.assertEqual(ui["analytics"]["cards"][0]["chart"]["variant"], "zone")
        self.assertEqual(ui["plan"]["target"], 22.0)

    def test_controller_status_includes_off_ui_contract(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="off"))

        controller.evaluate(runtime_state(ac_setpoint=22), integrations(30), now=1.0)

        ui = controller.status()["ui"]
        self.assertEqual(ui["summary"]["mode"], "off")
        self.assertEqual(ui["summary"]["authority"], "off")
        self.assertEqual(ui["summary"]["intent"], "off")
        self.assertEqual(ui["metrics"][0]["value"], "Off")

    def test_controller_status_includes_runtime_unavailable_ui_contract(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive"))

        controller.evaluate(None, integrations(30), now=1.0)

        ui = controller.status()["ui"]
        self.assertEqual(ui["summary"]["headline"], "Runtime state is not available")
        self.assertEqual(ui["summary"]["authority"], "control")
        self.assertEqual(ui["inputs"]["errors"], [])

    def test_controller_status_includes_missing_outside_temperature_ui_contract(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="weather"))

        controller.evaluate(runtime_state(ac_setpoint=22), integrations(None), now=1.0)

        ui = controller.status()["ui"]
        self.assertEqual(ui["summary"]["headline"], "Outside temperature is not available")
        self.assertIsNone(ui["inputs"]["outside_temperature"])
        self.assertEqual(ui["surfaces"]["environment"]["fields"][0]["value"], "-")
        self.assertEqual(ui["metrics"][1]["value"], "0 ready / 0 learning")

    def test_outside_temperature_skip_reason_does_not_replace_zone_state(self) -> None:
        contract = build_adaptive_ui_contract(
            {
                "mode": "adaptive",
                "config": {"control_strategy": "zone"},
                "note": "Outside temperature is not available",
                "outside_temperature": None,
                "learning": {
                    "zones": {
                        "0": {
                            "learn": True,
                            "last_skip_reason": "outside_temperature_unavailable",
                        }
                    }
                },
            }
        )

        self.assertEqual(contract["summary"]["headline"], "Outside temperature is not available")
        self.assertEqual(contract["analytics"]["cards"][0]["state"], "Learning")

    def test_controller_status_includes_weather_ui_contract(self) -> None:
        controller = AdaptiveController(AdaptiveConfig(mode="adaptive", control_strategy="weather", command_cooldown=1))

        controller.evaluate(runtime_state(ac_setpoint=24), integrations(20), now=1.0)

        ui = controller.status()["ui"]
        self.assertEqual(ui["summary"]["intent"], "turn_off")
        self.assertEqual(ui["surfaces"]["environment"]["fields"][0]["raw"], 20.0)
        self.assertEqual(ui["analytics"]["cards"][0]["chart"]["variant"], "environment")
        self.assertEqual(ui["commands"]["command_intents"][0]["intent"], "set_ac_power")
        self.assertEqual(ui["commands"]["command_intents"][0]["transaction"]["action"], "ac_status")

    def test_controller_status_includes_hybrid_ui_contract(self) -> None:
        controller = AdaptiveController(
            AdaptiveConfig(
                mode="adaptive",
                learning_mode="control",
                command_cooldown=1,
                control_zones=(0,),
                control_strategy="hybrid",
                hybrid_idle_damper_percent=10,
            )
        )
        seed_learning_model(controller, 0, ready_heating_model())

        controller.evaluate(
            runtime_state(ac_setpoint=20, zone_setpoint=22, zone_temperature=19, sensor_control=False, zone_percentage=25),
            integrations(30),
            now=1.0,
        )

        ui = controller.status()["ui"]
        self.assertEqual(ui["surfaces"]["hybrid"]["fields"][0]["label"], "Control Temperature")
        self.assertEqual(ui["metrics"][2]["raw"], 19.0)
        self.assertEqual(ui["analytics"]["cards"][0]["chart"]["variant"], "hybrid")
        self.assertEqual(ui["plan"]["control_temperature"], 19.0)
        self.assertEqual(ui["plan"]["damper_percentages"], {"0": 100})


if __name__ == "__main__":
    unittest.main()
