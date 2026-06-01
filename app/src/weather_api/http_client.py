"""Sync HTTP client factory for upstream weather requests."""

import httpx

DEFAULT_CONNECT_TIMEOUT_SECONDS = 5.0
DEFAULT_READ_TIMEOUT_SECONDS = 10.0


def create_http_client() -> httpx.Client:
    """Create a sync HTTP client with OpenWeatherMap timeout defaults.

    Returns:
        httpx.Client: Configured client for upstream weather calls.
    """
    timeout = httpx.Timeout(
        DEFAULT_READ_TIMEOUT_SECONDS,
        connect=DEFAULT_CONNECT_TIMEOUT_SECONDS,
    )
    return httpx.Client(timeout=timeout)
