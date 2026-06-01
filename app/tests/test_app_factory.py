"""Tests for application startup resource wiring."""

import httpx
import pytest
from fastapi.testclient import TestClient

from weather_api.application_resources import create_application_resources
from weather_api.config import Settings
from weather_api.main import create_app
from weather_api.providers.mock import MockWeatherProvider
from weather_api.providers.openweathermap import OpenWeatherMapProvider


def test_docs_endpoint_is_available() -> None:
    """OpenAPI docs are exposed for v1."""
    client = TestClient(create_app())

    response = client.get("/docs")

    assert response.status_code == 200


def test_factory_uses_mock_provider_by_default() -> None:
    """Default settings select the mock weather provider."""
    resources = create_application_resources(
        Settings(
            port=8000,
            weather_provider="mock",
            openweathermap_api_key=None,
            rate_limit_max_requests=60,
            rate_limit_window_seconds=60,
            enable_hsts=False,
        )
    )

    assert isinstance(resources.weather_provider, MockWeatherProvider)
    assert resources.shutdown_callbacks == ()


def test_factory_uses_openweathermap_provider_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WEATHER_PROVIDER=openweathermap selects the upstream provider."""
    monkeypatch.setenv("WEATHER_PROVIDER", "openweathermap")
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-key")

    app = create_app()

    assert isinstance(app.state.weather_provider, OpenWeatherMapProvider)
    assert len(app.state.shutdown_callbacks) == 1


def test_openweathermap_weather_route_returns_problem_detail_on_upstream_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Weather route maps upstream timeout to 502 problem+json."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    monkeypatch.setenv("WEATHER_PROVIDER", "openweathermap")
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-key")

    app = create_app()
    app.state.weather_provider = OpenWeatherMapProvider(
        api_key="test-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    client = TestClient(app)

    response = client.get("/weather", params={"city": "London"})

    assert response.status_code == 502
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["type"] == "https://weather-api.dnblabs.io/problems/upstream-weather-error"


def test_openweathermap_weather_route_returns_problem_detail_on_upstream_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Weather route maps upstream 404 to location-not-found problem+json."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=404, json={"cod": "404", "message": "not found"})

    monkeypatch.setenv("WEATHER_PROVIDER", "openweathermap")
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-key")

    app = create_app()
    app.state.weather_provider = OpenWeatherMapProvider(
        api_key="test-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    client = TestClient(app)

    response = client.get("/weather", params={"city": "Nowhere"})

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["type"] == "https://weather-api.dnblabs.io/problems/location-not-found"


def test_app_lifecycle_closes_openweathermap_http_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Application shutdown closes the OpenWeatherMap HTTP client."""
    monkeypatch.setenv("WEATHER_PROVIDER", "openweathermap")
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-key")

    app = create_app()
    provider = app.state.weather_provider
    assert isinstance(provider, OpenWeatherMapProvider)

    with TestClient(app) as client:
        response = client.get("/health/live")
        assert response.status_code == 200

    assert provider._client.is_closed
