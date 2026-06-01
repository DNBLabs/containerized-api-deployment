"""Tests for deterministic mock weather provider behavior."""

from weather_api.models import CityLocation
from weather_api.providers.mock import MockWeatherProvider


def test_mock_provider_returns_identical_summary_for_same_city() -> None:
    """Same city input yields stable mock weather across calls."""
    provider = MockWeatherProvider()
    location = CityLocation(kind="city", city="London")

    first = provider.get_current_weather(location)
    second = provider.get_current_weather(location)

    assert first.model_dump() == second.model_dump()
    assert first.provider == "mock"
