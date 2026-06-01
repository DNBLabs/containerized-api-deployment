"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from typing import Literal


def _parse_bool(value: str | None, *, default: bool) -> bool:
    """Parse common truthy/falsey environment string values."""
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    msg = f"Invalid boolean environment value: {value}"
    raise ValueError(msg)


def _parse_positive_int(value: str | None, *, default: int) -> int:
    """Parse a positive integer environment value."""
    if value is None:
        return default
    parsed = int(value)
    if parsed < 1:
        msg = f"Expected positive integer, got {parsed}."
        raise ValueError(msg)
    return parsed


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the weather API process."""

    port: int
    weather_provider: Literal["mock", "openweathermap"]
    openweathermap_api_key: str | None
    rate_limit_max_requests: int
    rate_limit_window_seconds: int
    enable_hsts: bool


def load_settings() -> Settings:
    """Load settings from the current process environment.

    Returns:
        Settings: Parsed runtime configuration with defaults applied.
    """
    provider_value = os.getenv("WEATHER_PROVIDER", "mock")
    if provider_value == "mock":
        weather_provider: Literal["mock", "openweathermap"] = "mock"
    elif provider_value == "openweathermap":
        weather_provider = "openweathermap"
    else:
        msg = f"Unsupported WEATHER_PROVIDER: {provider_value}"
        raise ValueError(msg)

    port_raw = os.getenv("PORT", "8000")
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")

    return Settings(
        port=int(port_raw),
        weather_provider=weather_provider,
        openweathermap_api_key=api_key if api_key else None,
        rate_limit_max_requests=_parse_positive_int(
            os.getenv("RATE_LIMIT_MAX_REQUESTS"),
            default=60,
        ),
        rate_limit_window_seconds=_parse_positive_int(
            os.getenv("RATE_LIMIT_WINDOW_SECONDS"),
            default=60,
        ),
        enable_hsts=_parse_bool(os.getenv("ENABLE_HSTS"), default=False),
    )
