"""Location query parsing and validation for weather requests."""

from weather_api.exceptions import LocationValidationError
from weather_api.models import CityLocation, CoordinateLocation, Location


def parse_location_query(
    city: str | None,
    lat: float | None,
    lon: float | None,
) -> Location:
    """Parse and validate mutually exclusive city or coordinate location input.

    Args:
        city: Optional city name from the query string.
        lat: Optional latitude from the query string.
        lon: Optional longitude from the query string.

    Returns:
        Location: Validated city or coordinate location.

    Raises:
        LocationValidationError: When input is missing, combined, or out of range.
    """
    normalized_city = city.strip() if city is not None else None
    has_city = normalized_city is not None and normalized_city != ""
    has_lat = lat is not None
    has_lon = lon is not None

    if has_city and (has_lat or has_lon):
        msg = "Provide either city or lat and lon, not both."
        raise LocationValidationError(msg)

    if has_lat != has_lon:
        msg = "Both lat and lon are required for coordinate queries."
        raise LocationValidationError(msg)

    if has_city:
        if not normalized_city or normalized_city.isspace():
            msg = "City must not be empty."
            raise LocationValidationError(msg)
        if len(normalized_city) < 2 or len(normalized_city) > 100:
            msg = "City must be between 2 and 100 characters."
            raise LocationValidationError(msg)
        return CityLocation(kind="city", city=normalized_city)

    if has_lat and has_lon:
        if lat is None or lon is None:
            msg = "Both lat and lon are required for coordinate queries."
            raise LocationValidationError(msg)
        if lat < -90 or lat > 90:
            msg = "Latitude must be between -90 and 90."
            raise LocationValidationError(msg)
        if lon < -180 or lon > 180:
            msg = "Longitude must be between -180 and 180."
            raise LocationValidationError(msg)
        return CoordinateLocation(kind="coords", lat=lat, lon=lon)

    msg = "Provide either city or lat and lon."
    raise LocationValidationError(msg)
