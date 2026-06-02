"""Integration tests for root Docker Compose stack (Task 13).

Validates compose config and host-reachable API with mock provider. Skipped when
Docker is unavailable.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PROJECT = "weather-api-compose-test"
HOST_BASE_URL = "http://127.0.0.1:8000"


def docker_is_available() -> bool:
    """Return True when the Docker CLI is on PATH and responds."""
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


pytestmark = pytest.mark.skipif(
    not docker_is_available(),
    reason="Docker CLI not available or daemon not running",
)


def _run_compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run docker compose from the repository root with an isolated project name."""
    return subprocess.run(
        ["docker", "compose", "-p", COMPOSE_PROJECT, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=check,
    )


def _wait_until_live(base_url: str, timeout_seconds: float = 120.0) -> None:
    """Poll liveness until the stack serves /health/live or timeout."""
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health/live", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
            last_error = error
        time.sleep(1.0)
    raise AssertionError(f"Compose stack did not become live at {base_url}") from last_error


@pytest.fixture(scope="module")
def compose_stack() -> Iterator[str]:
    """Build and start the compose stack once per module, then tear it down."""
    _run_compose("down", "-v", "--remove-orphans", check=False)
    up = _run_compose("up", "-d", "--build", check=False)
    assert up.returncode == 0, up.stderr or up.stdout
    try:
        _wait_until_live(HOST_BASE_URL)
        yield HOST_BASE_URL
    except AssertionError:
        logs = _run_compose("logs", "weather-api", check=False)
        log_tail = (logs.stdout or logs.stderr or "").strip()[-3000:]
        raise AssertionError(
            f"Compose project {COMPOSE_PROJECT} failed readiness. Logs:\n{log_tail}"
        ) from None
    finally:
        _run_compose("down", "-v", "--remove-orphans", check=False)


def test_compose_configuration_is_valid() -> None:
    """Root compose.yml renders to a valid compose configuration."""
    config = _run_compose("config", check=False)
    assert config.returncode == 0, config.stderr or config.stdout
    rendered = config.stdout
    assert "weather-api" in rendered
    assert "WEATHER_PROVIDER" in rendered
    assert "mock" in rendered
    assert 'published: "8000"' in rendered or "published: '8000'" in rendered
    assert "ENABLE_HSTS" in rendered


def test_compose_up_serves_weather_from_host(compose_stack: str) -> None:
    """docker compose up exposes GET /weather on the host with mock provider."""
    url = f"{compose_stack}/weather?city=London"
    with urllib.request.urlopen(url, timeout=5) as response:
        body = json.loads(response.read().decode())
    assert response.status == 200
    assert body["location"] == "London"
    assert body["provider"] == "mock"
