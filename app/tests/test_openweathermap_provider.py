"""Tests for OpenWeatherMap provider behavior with mocked HTTP."""

import httpx
import pytest

from weather_api.exceptions import (
    LocationNotFoundError,
    UpstreamRateLimitError,
    UpstreamWeatherError,
)
from weather_api.models import CityLocation
from weather_api.providers.openweathermap import OpenWeatherMapProvider

_OWM_FIXTURE = {
    "weather": [{"description": "Light Rain"}],
    "main": {"temp": 14.23, "humidity": 72},
    "wind": {"speed": 4.12},
    "name": "London",
    "sys": {"country": "GB"},
    "dt": 1_746_854_400,
}


def test_openweathermap_provider_maps_fixture_to_normalized_summary() -> None:
    """OpenWeatherMap JSON fixture maps to WeatherSummary with metric precision."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["units"] == "metric"
        assert request.url.params["q"] == "London"
        return httpx.Response(status_code=200, json=_OWM_FIXTURE)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenWeatherMapProvider(api_key="test-key", client=client)

    summary = provider.get_current_weather(CityLocation(kind="city", city="London"))

    assert summary.location == "London, GB"
    assert summary.temperature_c == 14.2
    assert summary.conditions == "light rain"
    assert summary.humidity_percent == 72
    assert summary.wind_speed_mps == 4.1
    assert summary.provider == "openweathermap"
    assert summary.observed_at.isoformat().endswith("+00:00")


def test_openweathermap_provider_maps_timeout_to_upstream_error() -> None:
    """Request timeout surfaces as UpstreamWeatherError."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenWeatherMapProvider(api_key="test-key", client=client)

    with pytest.raises(UpstreamWeatherError, match="timed out"):
        provider.get_current_weather(CityLocation(kind="city", city="London"))


def test_openweathermap_provider_maps_404_to_location_not_found() -> None:
    """Upstream 404 surfaces as LocationNotFoundError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=404, json={"cod": "404", "message": "not found"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenWeatherMapProvider(api_key="test-key", client=client)

    with pytest.raises(LocationNotFoundError):
        provider.get_current_weather(CityLocation(kind="city", city="Nowhere"))


def test_openweathermap_provider_maps_429_to_rate_limit_error() -> None:
    """Upstream 429 surfaces as UpstreamRateLimitError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=429, json={"cod": "429", "message": "limit"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenWeatherMapProvider(api_key="test-key", client=client)

    with pytest.raises(UpstreamRateLimitError):
        provider.get_current_weather(CityLocation(kind="city", city="London"))
