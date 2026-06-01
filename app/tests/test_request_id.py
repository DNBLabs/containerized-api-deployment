"""Tests for X-Request-ID request correlation middleware."""

import uuid

from fastapi.testclient import TestClient

from weather_api.main import create_app


def test_response_includes_generated_request_id_when_header_missing() -> None:
    """Missing X-Request-ID header causes server to generate one."""
    client = TestClient(create_app())

    response = client.get("/health/live")

    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    uuid.UUID(request_id)


def test_response_echoes_valid_client_request_id() -> None:
    """Valid client X-Request-ID is echoed on the response."""
    client = TestClient(create_app())
    client_request_id = "client-req-123"

    response = client.get("/health/live", headers={"X-Request-ID": client_request_id})

    assert response.headers.get("X-Request-ID") == client_request_id


def test_response_replaces_invalid_client_request_id_with_uuid() -> None:
    """Overlong client X-Request-ID is replaced with a generated UUID."""
    client = TestClient(create_app())
    invalid_request_id = "x" * 200

    response = client.get("/health/live", headers={"X-Request-ID": invalid_request_id})

    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert request_id != invalid_request_id
    uuid.UUID(request_id)
