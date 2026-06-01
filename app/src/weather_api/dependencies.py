"""FastAPI dependency providers for application-scoped services."""

from typing import Annotated, cast

from fastapi import Depends, Request

from weather_api.config import Settings
from weather_api.providers import WeatherProvider


def get_settings(request: Request) -> Settings:
    """Return settings captured when the application was created."""
    return cast(Settings, request.app.state.settings)


def get_weather_provider(request: Request) -> WeatherProvider:
    """Return the weather provider wired at application startup."""
    return cast(WeatherProvider, request.app.state.weather_provider)


SettingsDep = Annotated[Settings, Depends(get_settings)]
WeatherProviderDep = Annotated[WeatherProvider, Depends(get_weather_provider)]
