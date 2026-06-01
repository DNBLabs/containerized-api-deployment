"""Domain models for weather queries and normalized responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CityLocation(BaseModel):
    """Location specified by city name after validation and normalization."""

    kind: Literal["city"]
    city: str


class CoordinateLocation(BaseModel):
    """Location specified by geographic coordinates."""

    kind: Literal["coords"]
    lat: float
    lon: float


Location = CityLocation | CoordinateLocation


class WeatherSummary(BaseModel):
    """Normalized metric weather summary returned by all providers."""

    location: str
    temperature_c: float
    conditions: str
    humidity_percent: int = Field(ge=0, le=100)
    wind_speed_mps: float
    provider: Literal["mock", "openweathermap"]
    observed_at: datetime
