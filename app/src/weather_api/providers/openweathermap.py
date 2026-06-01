"""OpenWeatherMap weather provider implementation."""

from datetime import UTC, datetime
from typing import Any

import httpx

from weather_api.exceptions import (
    LocationNotFoundError,
    UpstreamRateLimitError,
    UpstreamWeatherError,
)
from weather_api.models import CityLocation, CoordinateLocation, Location, WeatherSummary

OPENWEATHERMAP_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


class OpenWeatherMapProvider:
    """Fetch and normalize current weather from OpenWeatherMap."""

    def __init__(self, api_key: str, client: httpx.Client) -> None:
        """Initialize provider with API credentials and HTTP client."""
        self._api_key = api_key
        self._client = client

    def get_current_weather(self, location: Location) -> WeatherSummary:
        """Return normalized weather from OpenWeatherMap for a location.

        Args:
            location: Validated city or coordinate location.

        Returns:
            WeatherSummary: Normalized upstream weather summary.

        Raises:
            LocationNotFoundError: When upstream returns 404 for the location.
            UpstreamRateLimitError: When upstream returns 429.
            UpstreamWeatherError: For timeouts, upstream 5xx, or invalid payloads.
        """
        params = self._build_params(location)

        try:
            response = self._client.get(OPENWEATHERMAP_WEATHER_URL, params=params)
        except httpx.TimeoutException as exc:
            msg = "OpenWeatherMap request timed out."
            raise UpstreamWeatherError(msg) from exc
        except httpx.HTTPError as exc:
            msg = "OpenWeatherMap request failed."
            raise UpstreamWeatherError(msg) from exc

        if response.status_code == 404:
            msg = "Location not found."
            raise LocationNotFoundError(msg)
        if response.status_code == 429:
            msg = "OpenWeatherMap rate limit exceeded."
            raise UpstreamRateLimitError(msg)
        if response.status_code in {401, 403} or response.status_code >= 500:
            msg = "OpenWeatherMap returned an upstream error."
            raise UpstreamWeatherError(msg)
        if response.status_code != 200:
            msg = "OpenWeatherMap returned an unexpected response."
            raise UpstreamWeatherError(msg)

        try:
            payload = response.json()
            return self._map_payload(payload)
        except (ValueError, KeyError, TypeError) as exc:
            msg = "OpenWeatherMap response could not be parsed."
            raise UpstreamWeatherError(msg) from exc

    def _build_params(self, location: Location) -> dict[str, str | float]:
        """Build OpenWeatherMap query parameters for a location."""
        params: dict[str, str | float] = {
            "appid": self._api_key,
            "units": "metric",
        }
        if isinstance(location, CityLocation):
            params["q"] = location.city
        elif isinstance(location, CoordinateLocation):
            params["lat"] = location.lat
            params["lon"] = location.lon
        else:
            msg = "Unsupported location type."
            raise TypeError(msg)
        return params

    def _map_payload(self, payload: dict[str, Any]) -> WeatherSummary:
        """Map OpenWeatherMap JSON payload to a normalized weather summary."""
        name = str(payload["name"])
        country = str(payload["sys"]["country"])
        weather_items = payload.get("weather", [])
        if not weather_items:
            msg = "OpenWeatherMap response missing weather conditions."
            raise UpstreamWeatherError(msg)

        description = str(weather_items[0]["description"]).lower()
        temperature = float(payload["main"]["temp"])
        humidity = int(payload["main"]["humidity"])
        wind_speed = float(payload["wind"]["speed"])
        observed_unix = int(payload["dt"])

        return WeatherSummary(
            location=f"{name}, {country}",
            temperature_c=round(temperature, 1),
            conditions=description,
            humidity_percent=humidity,
            wind_speed_mps=round(wind_speed, 1),
            provider="openweathermap",
            observed_at=datetime.fromtimestamp(observed_unix, tz=UTC),
        )

    def close(self) -> None:
        """Close the underlying HTTP client and release connection resources."""
        self._client.close()
