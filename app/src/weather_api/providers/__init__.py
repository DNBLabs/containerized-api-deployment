"""Weather provider interface for mock and upstream implementations."""

from typing import Protocol

from weather_api.models import Location, WeatherSummary


class WeatherProvider(Protocol):
    """Contract for fetching normalized current weather for a location."""

    def get_current_weather(self, location: Location) -> WeatherSummary:
        """Return current weather for the given location."""
        ...
