"""Application resource wiring for providers and shutdown hooks."""

from collections.abc import Callable
from dataclasses import dataclass

from weather_api.config import Settings
from weather_api.http_client import create_http_client
from weather_api.providers import WeatherProvider
from weather_api.providers.mock import MockWeatherProvider
from weather_api.providers.openweathermap import OpenWeatherMapProvider

ShutdownCallback = Callable[[], None]


@dataclass(frozen=True)
class ApplicationResources:
    """Runtime resources created during application startup."""

    weather_provider: WeatherProvider
    shutdown_callbacks: tuple[ShutdownCallback, ...]


def create_application_resources(settings: Settings) -> ApplicationResources:
    """Create provider and shutdown hooks for the configured runtime mode.

    Args:
        settings: Parsed application settings.

    Returns:
        ApplicationResources: Provider plus optional shutdown callbacks.
    """
    if settings.weather_provider == "mock":
        return ApplicationResources(
            weather_provider=MockWeatherProvider(),
            shutdown_callbacks=(),
        )

    provider = OpenWeatherMapProvider(
        api_key=settings.openweathermap_api_key or "",
        client=create_http_client(),
    )
    return ApplicationResources(
        weather_provider=provider,
        shutdown_callbacks=(provider.close,),
    )
