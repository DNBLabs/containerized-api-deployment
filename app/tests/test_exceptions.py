"""Tests for consolidated domain exception exports."""

import pytest

from weather_api.exceptions import LocationValidationError
from weather_api.location import parse_location_query


def test_location_validation_error_is_raised_from_parse_location_query() -> None:
    """Location validation failures surface through the shared exceptions module."""
    with pytest.raises(LocationValidationError, match="Provide either"):
        parse_location_query(city=None, lat=None, lon=None)
