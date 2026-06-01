"""Deterministic mock weather provider for local development and CI."""

import hashlib
from datetime import UTC, datetime

from weather_api.models import CityLocation, CoordinateLocation, Location, WeatherSummary

_MOCK_CONDITIONS = (
    "clear sky",
    "few clouds",
    "light rain",
    "overcast clouds",
    "scattered clouds",
)


class MockWeatherProvider:
    """Return stable hash-derived weather summaries without outbound HTTP."""

    def get_current_weather(self, location: Location) -> WeatherSummary:
        """Return deterministic mock weather for the given location.

        Args:
            location: Validated city or coordinate location.

        Returns:
            WeatherSummary: Stable mock summary with provider set to mock.
        """
        seed = self._location_seed(location)
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()

        temperature_raw = int(digest[0:8], 16) % 451
        humidity = int(digest[8:16], 16) % 101
        wind_raw = int(digest[16:24], 16) % 251
        condition_index = int(digest[24:32], 16) % len(_MOCK_CONDITIONS)
        observed_offset_seconds = int(digest[32:40], 16) % 86_400

        observed_at = datetime(2025, 1, 1, tzinfo=UTC).replace(
            second=observed_offset_seconds % 60,
            minute=(observed_offset_seconds // 60) % 60,
            hour=(observed_offset_seconds // 3600) % 24,
        )

        return WeatherSummary(
            location=self._display_location(location),
            temperature_c=round((temperature_raw / 10.0) - 10.0, 1),
            conditions=_MOCK_CONDITIONS[condition_index],
            humidity_percent=humidity,
            wind_speed_mps=round(wind_raw / 10.0, 1),
            provider="mock",
            observed_at=observed_at,
        )

    def _location_seed(self, location: Location) -> str:
        """Build a stable hash seed from normalized location input."""
        if isinstance(location, CityLocation):
            return f"city:{location.city.strip().casefold()}"
        if isinstance(location, CoordinateLocation):
            return f"coords:{location.lat:.4f},{location.lon:.4f}"
        msg = "Unsupported location type."
        raise TypeError(msg)

    def _display_location(self, location: Location) -> str:
        """Format the response location string for mock summaries."""
        if isinstance(location, CityLocation):
            return location.city
        if isinstance(location, CoordinateLocation):
            return f"{location.lat:.4f},{location.lon:.4f}"
        msg = "Unsupported location type."
        raise TypeError(msg)
