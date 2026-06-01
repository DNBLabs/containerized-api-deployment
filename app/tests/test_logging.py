"""Tests for structured JSON request logging middleware."""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from weather_api.main import create_app
from weather_api.middleware.logging import REQUEST_LOGGER_NAME


def test_weather_request_emits_structured_json_log(caplog: pytest.LogCaptureFixture) -> None:
    """Completed weather request emits one JSON log line with correlation fields."""
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER_NAME)
    client = TestClient(create_app())

    response = client.get("/weather", params={"city": "London"})

    assert response.status_code == 200
    request_logs = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == REQUEST_LOGGER_NAME
    ]
    assert len(request_logs) == 1
    payload = request_logs[0]
    assert payload["path"] == "/weather"
    assert payload["status_code"] == 200
    assert payload["provider"] == "mock"
    assert payload["request_id"] == response.headers.get("X-Request-ID")
    assert isinstance(payload["duration_ms"], float)
