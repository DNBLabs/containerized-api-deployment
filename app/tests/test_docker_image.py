"""Integration tests for the production Docker image (Task 12).

Exercises the container public interface: image build, non-root runtime, and HTTP
endpoints reachable from a running container. Skipped when Docker is unavailable.
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

APP_DIR = Path(__file__).resolve().parents[1]
IMAGE_TAG = "weather-api:test"
HOST_PORT = "18000"
BASE_URL = f"http://127.0.0.1:{HOST_PORT}"


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


def _run_docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a docker command and return the completed process."""
    return subprocess.run(
        ["docker", *args],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        check=check,
    )


@pytest.fixture(scope="module")
def built_image() -> str:
    """Build the production image once for the module."""
    build = _run_docker("build", "-t", IMAGE_TAG, ".", check=False)
    assert build.returncode == 0, build.stderr or build.stdout
    return IMAGE_TAG


@pytest.fixture
def running_api_container(built_image: str) -> Iterator[str]:
    """Start the API container with mock provider and tear it down after the test."""
    start = _run_docker(
        "run",
        "-d",
        "--rm",
        "-p",
        f"{HOST_PORT}:8000",
        "-e",
        "WEATHER_PROVIDER=mock",
        built_image,
        check=False,
    )
    assert start.returncode == 0, start.stderr or start.stdout
    container_id = start.stdout.strip()
    try:
        time.sleep(1.0)
        _wait_until_live(BASE_URL)
        yield BASE_URL
    except AssertionError:
        logs = _run_docker("logs", container_id, check=False)
        log_tail = (logs.stdout or logs.stderr or "").strip()[-2000:]
        raise AssertionError(
            f"Container {container_id} failed readiness at {BASE_URL}. Recent logs:\n{log_tail}"
        ) from None
    finally:
        _run_docker("rm", "-f", container_id, check=False)


def _wait_until_live(base_url: str, timeout_seconds: float = 45.0) -> None:
    """Poll liveness until the container serves /health/live or timeout."""
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health/live", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
            last_error = error
        time.sleep(0.5)
    raise AssertionError(f"Container did not become live at {base_url}") from last_error


def test_production_docker_image_builds() -> None:
    """Production Dockerfile produces a successful image build."""
    build = _run_docker("build", "-t", IMAGE_TAG, ".", check=False)
    assert build.returncode == 0, build.stderr or build.stdout


def test_production_container_runs_as_appuser(built_image: str) -> None:
    """Container process runs as dedicated non-root user appuser."""
    whoami = _run_docker("run", "--rm", built_image, "whoami", check=False)
    assert whoami.returncode == 0, whoami.stderr or whoami.stdout
    assert whoami.stdout.strip() == "appuser"


def test_production_container_serves_health_live(running_api_container: str) -> None:
    """Running container exposes liveness probe on /health/live."""
    with urllib.request.urlopen(f"{running_api_container}/health/live", timeout=5) as response:
        body = json.loads(response.read().decode())
    assert response.status == 200
    assert body == {"status": "ok"}


def test_production_container_serves_weather_with_mock_provider(
    running_api_container: str,
) -> None:
    """Running container serves GET /weather with mock provider enabled."""
    url = f"{running_api_container}/weather?city=London"
    with urllib.request.urlopen(url, timeout=5) as response:
        body = json.loads(response.read().decode())
    assert response.status == 200
    assert body["location"] == "London"
    assert body["provider"] == "mock"
    assert "temperature_c" in body
