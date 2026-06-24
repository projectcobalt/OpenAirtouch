"""MQTT state publishing and Home Assistant discovery."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

LOG = logging.getLogger("uvicorn.error")


@dataclass(frozen=True)
class MqttConfig:
    enabled: bool = False
    host: str = ""
    port: int = 1883
    username: str = ""
    password: str = ""
    discovery: bool = True
    discovery_prefix: str = "homeassistant"
    topic_prefix: str = "airtouch4"
    client_id: str = "airtouch4-touchpad-host"
    publish_interval: float = 10.0

    @property
    def broker_host(self) -> str:
        return self.host.strip() or "core-mosquitto"


class MqttStatePublisher:
    def __init__(self, config: MqttConfig) -> None:
        self.config = config
        self._client: Any = None
        self._connected = False
        self._error: str | None = None
        self._published_discovery: set[str] = set()

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "connected": self._connected,
            "host": self.config.broker_host if self.config.enabled else "",
            "port": self.config.port,
            "error": self._error,
        }

    def publish(self, snapshot: dict[str, Any]) -> None:
        if not self.config.enabled:
            return
        if not self._ensure_connected():
            return
        runtime = snapshot.get("runtime") or {}
        state = runtime.get("state") or {}
        self._publish_json(f"{self.config.topic_prefix}/state", snapshot)
        self._publish_availability("online")
        if self.config.discovery:
            self._publish_discovery(state)
        self._publish_entities(state)

    def stop(self) -> None:
        if self._client is None:
            return
        try:
            self._publish_availability("offline")
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:  # pragma: no cover - defensive shutdown
            LOG.debug("MQTT shutdown failed", exc_info=True)
        finally:
            self._connected = False

    def _ensure_connected(self) -> bool:
        if self._connected:
            return True
        try:
            import paho.mqtt.client as mqtt
        except ModuleNotFoundError as exc:
            self._error = "paho-mqtt is not installed"
            LOG.warning("MQTT disabled: %s", self._error)
            return False
        try:
            client = mqtt.Client(client_id=self.config.client_id)
            if self.config.username:
                client.username_pw_set(self.config.username, self.config.password or None)
            client.will_set(f"{self.config.topic_prefix}/availability", "offline", retain=True)
            client.connect(self.config.broker_host, self.config.port, keepalive=30)
            client.loop_start()
            self._client = client
            self._connected = True
            self._error = None
            LOG.info("MQTT connected to %s:%s", self.config.broker_host, self.config.port)
            return True
        except Exception as exc:  # pragma: no cover - live network path
            self._error = f"{type(exc).__name__}: {exc}"
            self._connected = False
            LOG.warning("MQTT connection failed: %s", self._error)
            return False

    def _publish_discovery(self, state: dict[str, Any]) -> None:
        device = {
            "identifiers": ["airtouch4_touchpad_host"],
            "name": "AirTouch Touchpad Host",
            "manufacturer": "Polyaire",
            "model": "AirTouch",
        }
        for ac_id, ac in sorted((state.get("acs") or {}).items(), key=lambda item: int(item[0])):
            base = ac.get("base") or {}
            name = base.get("name") or f"AC {int(ac_id) + 1}"
            object_id = f"airtouch4_ac_{int(ac_id) + 1}"
            payload = {
                "name": name,
                "unique_id": f"{object_id}_climate",
                "object_id": object_id,
                "device": device,
                "availability_topic": f"{self.config.topic_prefix}/availability",
                "current_temperature_topic": f"{self.config.topic_prefix}/ac/{ac_id}/current_temperature",
                "temperature_state_topic": f"{self.config.topic_prefix}/ac/{ac_id}/target_temperature",
                "mode_state_topic": f"{self.config.topic_prefix}/ac/{ac_id}/mode",
                "fan_mode_state_topic": f"{self.config.topic_prefix}/ac/{ac_id}/fan_mode",
                "modes": ["off", "auto", "heat", "dry", "fan_only", "cool"],
                "fan_modes": ["auto", "low", "medium", "high"],
                "temperature_unit": "C",
                "precision": 1.0,
                "temp_step": 1.0,
            }
            self._publish_discovery_once("climate", object_id, payload)
        for group_id, group in sorted((state.get("active_groups") or state.get("groups") or {}).items(), key=lambda item: int(item[0])):
            status = group.get("status") or {}
            if not status.get("has_sensor"):
                continue
            name = group.get("name") or f"Zone {int(group_id) + 1}"
            object_id = f"airtouch4_zone_{int(group_id) + 1}"
            payload = {
                "name": name,
                "unique_id": f"{object_id}_climate",
                "object_id": object_id,
                "device": device,
                "availability_topic": f"{self.config.topic_prefix}/availability",
                "current_temperature_topic": f"{self.config.topic_prefix}/zone/{group_id}/current_temperature",
                "temperature_state_topic": f"{self.config.topic_prefix}/zone/{group_id}/target_temperature",
                "mode_state_topic": f"{self.config.topic_prefix}/zone/{group_id}/mode",
                "modes": ["off", "heat_cool"],
                "temperature_unit": "C",
                "precision": 1.0,
                "temp_step": 1.0,
            }
            self._publish_discovery_once("climate", object_id, payload)

    def _publish_entities(self, state: dict[str, Any]) -> None:
        mode_names = {0: "auto", 1: "heat", 2: "dry", 3: "fan_only", 4: "cool"}
        fan_names = {0: "auto", 1: "low", 2: "medium", 3: "high"}
        for ac_id, ac in (state.get("acs") or {}).items():
            status = ac.get("status") or {}
            mode = "off" if status.get("power_on") is False else mode_names.get(status.get("mode"), "auto")
            self._publish_value(f"{self.config.topic_prefix}/ac/{ac_id}/mode", mode)
            self._publish_value(f"{self.config.topic_prefix}/ac/{ac_id}/fan_mode", fan_names.get(status.get("fan"), "auto"))
            self._publish_value(f"{self.config.topic_prefix}/ac/{ac_id}/target_temperature", status.get("setpoint"))
            self._publish_value(f"{self.config.topic_prefix}/ac/{ac_id}/current_temperature", status.get("sensor_temp"))
        for group_id, group in (state.get("active_groups") or state.get("groups") or {}).items():
            status = group.get("status") or {}
            mode = "heat_cool" if status.get("power_name") in {"on", "turbo"} else "off"
            self._publish_value(f"{self.config.topic_prefix}/zone/{group_id}/mode", mode)
            self._publish_value(f"{self.config.topic_prefix}/zone/{group_id}/target_temperature", status.get("setpoint"))
            self._publish_value(f"{self.config.topic_prefix}/zone/{group_id}/current_temperature", status.get("temperature"))
            self._publish_value(f"{self.config.topic_prefix}/zone/{group_id}/percentage", status.get("percentage"))

    def _publish_discovery_once(self, component: str, object_id: str, payload: dict[str, Any]) -> None:
        key = f"{component}/{object_id}"
        if key in self._published_discovery:
            return
        topic = f"{self.config.discovery_prefix}/{component}/{object_id}/config"
        self._publish_json(topic, payload, retain=True)
        self._published_discovery.add(key)

    def _publish_availability(self, value: str) -> None:
        self._publish_value(f"{self.config.topic_prefix}/availability", value, retain=True)

    def _publish_json(self, topic: str, payload: dict[str, Any], *, retain: bool = False) -> None:
        if self._client is not None:
            self._client.publish(topic, json.dumps(payload, separators=(",", ":"), default=str), qos=0, retain=retain)

    def _publish_value(self, topic: str, value: Any, *, retain: bool = False) -> None:
        if value is None or self._client is None:
            return
        self._client.publish(topic, str(value), qos=0, retain=retain)
