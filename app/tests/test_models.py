"""Unit tests for domain model serialization."""

from datetime import UTC, datetime

from weather_api.models import CityLocation, CoordinateLocation, WeatherSummary


def test_weather_summary_serializes_to_json_compatible_dict() -> None:
    """WeatherSummary round-trips through JSON-friendly model_dump output."""
    summary = WeatherSummary(
        location="London, GB",
        temperature_c=14.2,
        conditions="light rain",
        humidity_percent=72,
        wind_speed_mps=4.1,
        provider="openweathermap",
        observed_at=datetime(2025, 6, 1, 12, 0, tzinfo=UTC),
    )

    payload = summary.model_dump(mode="json")

    assert payload["location"] == "London, GB"
    assert payload["temperature_c"] == 14.2
    assert payload["provider"] == "openweathermap"
    assert payload["observed_at"] == "2025-06-01T12:00:00Z"
    assert WeatherSummary.model_validate(payload) == summary


def test_city_location_serializes_with_discriminator() -> None:
    """CityLocation includes the city kind discriminator in JSON output."""
    location = CityLocation(kind="city", city="London")

    payload = location.model_dump(mode="json")

    assert payload == {"kind": "city", "city": "London"}
    assert CityLocation.model_validate(payload) == location


def test_coordinate_location_serializes_with_discriminator() -> None:
    """CoordinateLocation includes the coords kind discriminator in JSON output."""
    location = CoordinateLocation(kind="coords", lat=51.5, lon=-0.12)

    payload = location.model_dump(mode="json")

    assert payload == {"kind": "coords", "lat": 51.5, "lon": -0.12}
    assert CoordinateLocation.model_validate(payload) == location
