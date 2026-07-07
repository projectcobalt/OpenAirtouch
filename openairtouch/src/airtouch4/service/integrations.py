"""Home Assistant integration polling state for the runtime service."""

from __future__ import annotations

import time
from typing import Any

from .ha_client import HomeAssistantApiClient, HomeAssistantApiConfig


class HomeAssistantIntegrationPoller:
    """Polls Home Assistant-backed inputs and shapes their service snapshot."""

    def __init__(
        self,
        config: HomeAssistantApiConfig,
        *,
        poll_interval: float = 60.0,
        client: HomeAssistantApiClient | None = None,
    ) -> None:
        self.config = config
        self.client = client or HomeAssistantApiClient(config)
        self.poll_interval = poll_interval
        self.weather: dict[str, Any] | None = None
        self.weather_error: str | None = None
        self.forecast: dict[str, Any] | None = None
        self.forecast_error: str | None = None
        self.indoor: dict[str, Any] | None = None
        self.indoor_error: str | None = None
        self.solar: dict[str, Any] | None = None
        self.solar_error: str | None = None
        self.ac_telemetry: dict[str, Any] | None = None
        self.ac_telemetry_error: str | None = None
        self.sun: dict[str, Any] | None = None
        self.sun_error: str | None = None
        self._next_poll = 0.0

    def snapshot(self) -> dict[str, Any]:
        return {
            "weather": {
                "entity_id": self.config.weather_entity,
                "state": self.weather,
                "error": self.weather_error,
            },
            "indoor": {
                "temperature_entity_id": self.config.indoor_temperature_entity,
                "humidity_entity_id": self.config.indoor_humidity_entity,
                "co2_entity_id": self.config.indoor_co2_entity,
                "state": self.indoor,
                "error": self.indoor_error,
            },
            "forecast": {
                "entity_id": self.config.forecast_weather_entity,
                "state": self.forecast,
                "error": self.forecast_error,
            },
            "solar": {
                "irradiance_entity_id": self.config.solar_irradiance_entity,
                "cloud_cover_entity_id": self.config.cloud_cover_entity,
                "state": self.solar,
                "error": self.solar_error,
            },
            "ac_telemetry": {
                "power_entity_id": self.config.ac_power_entity,
                "running_entity_id": self.config.ac_running_entity,
                "frequency_entity_id": self.config.ac_frequency_entity,
                "return_air_temp_entity_id": self.config.ac_return_air_temp_entity,
                "supply_air_temp_entity_id": self.config.ac_supply_air_temp_entity,
                "state": self.ac_telemetry,
                "error": self.ac_telemetry_error,
            },
            "sun": {
                "state": self.sun,
                "error": self.sun_error,
            },
        }

    def runtime_inputs(self) -> dict[str, Any]:
        return {
            "weather": {"state": self.weather, "error": self.weather_error},
            "indoor": {"state": self.indoor, "error": self.indoor_error},
            "forecast": {"state": self.forecast, "error": self.forecast_error},
            "solar": {"state": self.solar, "error": self.solar_error},
            "ac_telemetry": {"state": self.ac_telemetry, "error": self.ac_telemetry_error},
            "sun": {"state": self.sun, "error": self.sun_error},
        }

    def indoor_input(self) -> dict[str, Any]:
        return {"indoor": {"state": self.indoor, "error": self.indoor_error}}

    def home_assistant_timezone(self) -> str | None:
        return self.client.home_assistant_timezone()

    def poll(self, *, now: float | None = None) -> bool:
        if not self._configured():
            return False
        current = time.monotonic() if now is None else now
        if current < self._next_poll:
            return False
        self._next_poll = current + max(10.0, self.poll_interval)

        changed = False
        changed = self._poll_weather() or changed
        changed = self._poll_forecast() or changed
        changed = self._poll_indoor() or changed
        changed = self._poll_solar() or changed
        changed = self._poll_ac_telemetry() or changed
        changed = self._poll_sun() or changed
        return changed

    def _configured(self) -> bool:
        return any((
            self._weather_entity(),
            self._forecast_entity(),
            self._indoor_configured(),
            self._solar_configured(),
            self._telemetry_configured(),
        ))

    def _weather_entity(self) -> str:
        return self.config.weather_entity.strip()

    def _forecast_entity(self) -> str:
        return self.config.forecast_weather_entity.strip()

    def _indoor_configured(self) -> bool:
        return any((
            self.config.indoor_temperature_entity.strip(),
            self.config.indoor_humidity_entity.strip(),
            self.config.indoor_co2_entity.strip(),
        ))

    def _solar_configured(self) -> bool:
        return any((
            self.config.solar_irradiance_entity.strip(),
            self.config.cloud_cover_entity.strip(),
        ))

    def _telemetry_configured(self) -> bool:
        return any(
            entity.strip()
            for entity in (
                self.config.ac_power_entity,
                self.config.ac_running_entity,
                self.config.ac_frequency_entity,
                self.config.ac_return_air_temp_entity,
                self.config.ac_supply_air_temp_entity,
            )
        )

    def _poll_weather(self) -> bool:
        entity = self._weather_entity()
        if not entity:
            return self._set("weather", None, None)
        try:
            weather = self.client.weather_snapshot()
            error = _weather_data_quality_error(weather, entity)
            return self._set("weather", weather, error)
        except Exception as exc:  # pragma: no cover - live HA API path
            return self._set("weather", self.weather, f"{type(exc).__name__}: {exc}")

    def _poll_forecast(self) -> bool:
        if not self._forecast_entity():
            return self._set("forecast", None, None)
        try:
            forecast = self.client.hourly_forecast_snapshot(current_weather=self.weather)
            return self._set("forecast", forecast, None)
        except Exception as exc:  # pragma: no cover - live HA API path
            return self._set("forecast", self.forecast, f"{type(exc).__name__}: {exc}")

    def _poll_indoor(self) -> bool:
        if not self._indoor_configured():
            return self._set("indoor", None, None)
        try:
            return self._set("indoor", self.client.indoor_snapshot(), None)
        except Exception as exc:  # pragma: no cover - live HA API path
            return self._set("indoor", self.indoor, f"{type(exc).__name__}: {exc}")

    def _poll_solar(self) -> bool:
        if not self._solar_configured():
            return self._set("solar", None, None)
        try:
            return self._set("solar", self.client.solar_snapshot(), None)
        except Exception as exc:  # pragma: no cover - live HA API path
            return self._set("solar", self.solar, f"{type(exc).__name__}: {exc}")

    def _poll_ac_telemetry(self) -> bool:
        if not self._telemetry_configured():
            return self._set("ac_telemetry", None, None)
        try:
            return self._set("ac_telemetry", self.client.ac_telemetry_snapshot(), None)
        except Exception as exc:  # pragma: no cover - live HA API path
            return self._set("ac_telemetry", self.ac_telemetry, f"{type(exc).__name__}: {exc}")

    def _poll_sun(self) -> bool:
        if not (self._weather_entity() or self._solar_configured()):
            return self._set("sun", None, None)
        try:
            return self._set("sun", self.client.sun_snapshot(), None)
        except Exception as exc:  # pragma: no cover - live HA API path
            return self._set("sun", self.sun, f"{type(exc).__name__}: {exc}")

    def _set(self, name: str, state: dict[str, Any] | None, error: str | None) -> bool:
        state_attr = name
        error_attr = f"{name}_error"
        changed = getattr(self, state_attr) != state or getattr(self, error_attr) != error
        setattr(self, state_attr, state)
        setattr(self, error_attr, error)
        return changed


def _weather_data_quality_error(weather: dict[str, Any] | None, entity_id: str) -> str | None:
    if not weather:
        return None
    if _float_or_none(weather.get("temperature")) is None:
        return f"{entity_id} has no numeric temperature"
    return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
