"""Security hardening tests for headers, rate limits, and error handling."""

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from weather_api.application_resources import create_application_resources
from weather_api.config import load_settings
from weather_api.errors import register_exception_handlers
from weather_api.main import create_app
from weather_api.middleware.rate_limit import RateLimitMiddleware, create_rate_limit_store
from weather_api.middleware.request_id import RequestIdMiddleware
from weather_api.middleware.security_headers import SecurityHeadersMiddleware


def test_security_headers_are_present_on_responses() -> None:
    """Baseline security headers are attached to API responses."""
    client = TestClient(create_app())

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers


def test_hsts_header_is_set_when_enabled_and_request_is_https(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HSTS is emitted behind HTTPS when ENABLE_HSTS=true."""
    monkeypatch.setenv("ENABLE_HSTS", "true")
    client = TestClient(create_app(), base_url="https://testserver")

    response = client.get("/health/live")

    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


def test_rate_limit_returns_problem_detail_when_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public routes return RFC 7807 429 when client exceeds configured limit."""
    monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "2")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    client = TestClient(create_app())

    assert client.get("/weather?city=London").status_code == 200
    assert client.get("/weather?city=Paris").status_code == 200
    response = client.get("/weather?city=Berlin")

    assert response.status_code == 429
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["type"] == "https://weather-api.dnblabs.io/problems/rate-limit-exceeded"


def test_health_endpoints_are_exempt_from_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Health probes remain reachable even when weather rate limit is exhausted."""
    monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "1")
    client = TestClient(create_app())

    assert client.get("/weather?city=London").status_code == 200
    assert client.get("/weather?city=Paris").status_code == 429
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_unhandled_exception_returns_generic_internal_problem_detail() -> None:
    """Unexpected server errors do not leak exception details to clients."""

    def failing_app() -> FastAPI:
        settings = load_settings()
        app = FastAPI(debug=False)
        resources = create_application_resources(settings)
        app.state.settings = settings
        app.state.weather_provider = resources.weather_provider
        app.state.shutdown_callbacks = resources.shutdown_callbacks
        app.state.rate_limit_store = create_rate_limit_store()
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RateLimitMiddleware)
        app.add_middleware(RequestIdMiddleware)
        register_exception_handlers(app)
        router = APIRouter()

        @router.get("/boom")
        def boom() -> None:
            msg = "super secret internals"
            raise RuntimeError(msg)

        app.include_router(router)
        return app

    client = TestClient(failing_app(), raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["type"] == "https://weather-api.dnblabs.io/problems/internal-error"
    assert body["detail"] == "An unexpected error occurred."
    assert "secret" not in response.text
