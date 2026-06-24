"""Small Home Assistant API client for add-on local reads."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class HomeAssistantApiConfig:
    weather_entity: str = ""
    timeout: float = 3.0


class HomeAssistantApiClient:
    def __init__(self, config: HomeAssistantApiConfig) -> None:
        self.config = config

    def weather_snapshot(self) -> dict[str, Any] | None:
        entity_id = self.config.weather_entity.strip()
        if not entity_id:
            return None
        state = self.read_state(entity_id)
        attrs = state.get("attributes", {})
        return {
            "entity_id": entity_id,
            "state": state.get("state"),
            "temperature": attrs.get("temperature"),
            "humidity": attrs.get("humidity"),
            "wind_speed": attrs.get("wind_speed"),
            "wind_bearing": attrs.get("wind_bearing"),
            "pressure": attrs.get("pressure"),
            "forecast": attrs.get("forecast"),
            "friendly_name": attrs.get("friendly_name"),
            "temperature_unit": attrs.get("temperature_unit"),
            "pressure_unit": attrs.get("pressure_unit"),
            "wind_speed_unit": attrs.get("wind_speed_unit"),
        }

    def read_state(self, entity_id: str) -> dict[str, Any]:
        token = os.environ.get("SUPERVISOR_TOKEN", "")
        if not token:
            raise RuntimeError("SUPERVISOR_TOKEN is not available")
        url = f"http://supervisor/core/api/states/{quote(entity_id, safe='')}"
        request = Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })
        try:
            with urlopen(request, timeout=self.config.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"could not read {entity_id}: {exc}") from exc
