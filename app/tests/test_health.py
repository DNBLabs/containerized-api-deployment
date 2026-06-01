"""Tests for health probe HTTP endpoints."""

import pytest
from fastapi.testclient import TestClient

from weather_api.main import create_app


def test_health_live_returns_ok() -> None:
    """Liveness probe returns 200 with status ok."""
    client = TestClient(create_app())

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_returns_ready_in_mock_mode_without_api_key() -> None:
    """Readiness probe passes in mock mode without upstream API key."""
    client = TestClient(create_app())

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_health_ready_returns_not_ready_when_openweathermap_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Readiness probe fails when live provider is configured without API key."""
    monkeypatch.setenv("WEATHER_PROVIDER", "openweathermap")
    monkeypatch.delenv("OPENWEATHERMAP_API_KEY", raising=False)
    client = TestClient(create_app())

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "reason": "missing_openweathermap_api_key",
    }


def test_health_ready_uses_startup_settings_not_later_env_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Readiness reflects settings captured at app startup, not a fresh env read."""
    monkeypatch.setenv("WEATHER_PROVIDER", "mock")
    app = create_app()
    client = TestClient(app)

    monkeypatch.setenv("WEATHER_PROVIDER", "openweathermap")
    monkeypatch.delenv("OPENWEATHERMAP_API_KEY", raising=False)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
