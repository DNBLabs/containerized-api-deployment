"""Integration tests for location query parsing."""

import pytest

from weather_api.exceptions import LocationValidationError
from weather_api.location import parse_location_query
from weather_api.models import CityLocation, CoordinateLocation


def test_parse_location_query_accepts_city_only() -> None:
    """City-only query returns a CityLocation."""
    location = parse_location_query(city="London", lat=None, lon=None)

    assert isinstance(location, CityLocation)
    assert location.city == "London"


def test_parse_location_query_accepts_coordinates_only() -> None:
    """Lat/lon query returns a CoordinateLocation."""
    location = parse_location_query(city=None, lat=51.5, lon=-0.12)

    assert isinstance(location, CoordinateLocation)
    assert location.lat == 51.5
    assert location.lon == -0.12


def test_parse_location_query_rejects_city_and_coordinates() -> None:
    """City plus coordinates raises LocationValidationError."""
    with pytest.raises(LocationValidationError, match="not both"):
        parse_location_query(city="London", lat=51.5, lon=-0.12)


def test_parse_location_query_rejects_missing_location() -> None:
    """Missing city and coordinates raises LocationValidationError."""
    with pytest.raises(LocationValidationError, match="Provide either"):
        parse_location_query(city=None, lat=None, lon=None)


def test_parse_location_query_rejects_out_of_range_latitude() -> None:
    """Out-of-range latitude raises LocationValidationError."""
    with pytest.raises(LocationValidationError, match="Latitude"):
        parse_location_query(city=None, lat=91.0, lon=0.0)
