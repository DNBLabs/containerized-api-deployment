"""Integration tests for the public weather HTTP API."""

import pytest
from fastapi.testclient import TestClient

from weather_api.main import create_app


def test_get_weather_by_city_returns_normalized_mock_summary() -> None:
    """GET /weather?city=London returns 200 with mock WeatherSummary shape."""
    client = TestClient(create_app())

    response = client.get("/weather", params={"city": "London"})

    assert response.status_code == 200
    body = response.json()
    assert body["location"] == "London"
    assert body["provider"] == "mock"
    assert isinstance(body["temperature_c"], float)
    assert isinstance(body["conditions"], str)
    assert isinstance(body["humidity_percent"], int)
    assert isinstance(body["wind_speed_mps"], float)
    assert body["observed_at"].endswith("Z")


def test_get_weather_by_coordinates_returns_normalized_mock_summary() -> None:
    """GET /weather?lat=51.5&lon=-0.12 returns 200 with coordinate location label."""
    client = TestClient(create_app())

    response = client.get("/weather", params={"lat": 51.5, "lon": -0.12})

    assert response.status_code == 200
    body = response.json()
    assert body["location"] == "51.5000,-0.1200"
    assert body["provider"] == "mock"


def test_get_weather_rejects_city_and_coordinates_with_problem_detail() -> None:
    """GET /weather with city and coordinates returns 422 problem+json."""
    client = TestClient(create_app())

    response = client.get(
        "/weather",
        params={"city": "London", "lat": 51.5, "lon": -0.12},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["type"] == "https://weather-api.dnblabs.io/problems/invalid-location"
    assert body["title"] == "Invalid location query"
    assert body["status"] == 422
    assert "not both" in body["detail"].lower()


def test_weather_uses_startup_provider_not_later_env_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Weather requests use the provider wired at startup after env changes."""
    monkeypatch.setenv("WEATHER_PROVIDER", "mock")
    client = TestClient(create_app())

    monkeypatch.setenv("WEATHER_PROVIDER", "openweathermap")
    monkeypatch.delenv("OPENWEATHERMAP_API_KEY", raising=False)

    response = client.get("/weather", params={"city": "London"})

    assert response.status_code == 200
    assert response.json()["provider"] == "mock"
