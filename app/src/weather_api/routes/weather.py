"""Weather HTTP routes for the tracer API."""

from fastapi import APIRouter, Query, Request

from weather_api.dependencies import WeatherProviderDep
from weather_api.location import parse_location_query
from weather_api.models import WeatherSummary

router = APIRouter(tags=["weather"])


@router.get("/weather", response_model=WeatherSummary)
def get_weather(
    request: Request,
    provider: WeatherProviderDep,
    city: str | None = Query(default=None),
    lat: float | None = Query(default=None),
    lon: float | None = Query(default=None),
) -> WeatherSummary:
    """Return current weather for a validated city or coordinate query."""
    location = parse_location_query(city=city, lat=lat, lon=lon)
    summary = provider.get_current_weather(location)
    request.state.weather_provider = summary.provider
    return summary
