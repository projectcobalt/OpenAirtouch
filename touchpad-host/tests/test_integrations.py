from __future__ import annotations

import json
import unittest

from airtouch4.service.ha_client import HomeAssistantApiClient, HomeAssistantApiConfig
from airtouch4.service.mqtt import MqttConfig, MqttStatePublisher


class FakeMqttClient:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, bool]] = []

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> "FakePublishInfo":
        self.messages.append((topic, payload, retain))
        return FakePublishInfo()


class FakePublishInfo:
    rc = 0

    def wait_for_publish(self, timeout: float | None = None) -> None:
        return


class FakeHaClient(HomeAssistantApiClient):
    def __init__(self, config: HomeAssistantApiConfig, states: dict[str, dict]) -> None:
        super().__init__(config)
        self.states = states

    def read_state(self, entity_id: str) -> dict:
        return self.states[entity_id]


class IntegrationConfigTests(unittest.TestCase):
    def test_mqtt_blank_host_defaults_to_mosquitto_addon(self) -> None:
        self.assertEqual(MqttConfig(enabled=True).broker_host, "core-mosquitto")
        self.assertEqual(MqttConfig(host="mqtt.local").broker_host, "mqtt.local")
        self.assertEqual(MqttConfig(enabled=True).broker_port, 1883)

    def test_mqtt_disabled_publisher_is_noop(self) -> None:
        publisher = MqttStatePublisher(MqttConfig(enabled=False))

        publisher.publish({"runtime": {"state": {}}})

        self.assertFalse(publisher.status()["connected"])
        self.assertIsNone(publisher.status()["error"])

    def test_mqtt_publishes_discovery_and_status_counts(self) -> None:
        publisher = MqttStatePublisher(MqttConfig(enabled=True))
        fake = FakeMqttClient()
        publisher._client = fake
        publisher._connected = True

        publisher.publish({
            "runtime": {
                "state": {
                    "acs": {0: {"base": {"name": "AC"}, "status": {"power_on": True, "mode": 4, "fan": 2, "setpoint": 23, "sensor_temp": 22}}},
                    "groups": {0: {"name": "Kitchen", "status": {"has_sensor": True, "power_name": "on", "setpoint": 23, "temperature": 22, "percentage": 80}}},
                    "active_groups": {0: {"name": "Kitchen", "status": {"has_sensor": True, "power_name": "on", "setpoint": 23, "temperature": 22, "percentage": 80}}},
                },
            },
        })

        status = publisher.status()
        self.assertEqual(status["publish_count"], 1)
        self.assertEqual(status["discovery_count"], 8)
        self.assertEqual(status["last_publish"]["acs"], 1)
        self.assertEqual(status["last_publish"]["active_groups"], 1)
        discovery = {
            topic: json.loads(payload)
            for topic, payload, retain in fake.messages
            if topic.startswith("homeassistant/sensor/")
        }
        self.assertIn("homeassistant/sensor/airtouch4_ac_1_current_temperature/config", discovery)
        self.assertEqual(discovery["homeassistant/sensor/airtouch4_ac_1_current_temperature/config"]["unit_of_measurement"], "°C")

    def test_weather_config_defaults_to_no_entity(self) -> None:
        self.assertEqual(HomeAssistantApiConfig().weather_entity, "")
        self.assertEqual(HomeAssistantApiConfig().indoor_temperature_entity, "")
        self.assertEqual(HomeAssistantApiConfig().indoor_humidity_entity, "")

    def test_indoor_snapshot_reads_configured_ha_sensors(self) -> None:
        client = FakeHaClient(
            HomeAssistantApiConfig(
                indoor_temperature_entity="sensor.lounge_temperature",
                indoor_humidity_entity="sensor.lounge_humidity",
            ),
            {
                "sensor.lounge_temperature": {
                    "state": "22.4",
                    "attributes": {"unit_of_measurement": "C", "friendly_name": "Lounge temperature"},
                },
                "sensor.lounge_humidity": {
                    "state": "54",
                    "attributes": {"unit_of_measurement": "%", "friendly_name": "Lounge humidity"},
                },
            },
        )

        snapshot = client.indoor_snapshot()

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["temperature"], 22.4)
        self.assertEqual(snapshot["humidity"], 54.0)
        self.assertEqual(snapshot["temperature_entity_id"], "sensor.lounge_temperature")
        self.assertEqual(snapshot["humidity_entity_id"], "sensor.lounge_humidity")


if __name__ == "__main__":
    unittest.main()
