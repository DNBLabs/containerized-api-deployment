"""RFC 7807 problem detail helpers and exception handlers."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from weather_api.exceptions import (
    LocationNotFoundError,
    LocationValidationError,
    UpstreamRateLimitError,
    UpstreamWeatherError,
)

PROBLEM_BASE_URL = "https://weather-api.dnblabs.io/problems/"
_ERROR_LOGGER = logging.getLogger("weather_api.errors")
_GENERIC_VALIDATION_DETAIL = "The weather query parameters are invalid."
_GENERIC_INTERNAL_DETAIL = "An unexpected error occurred."


def build_problem_body(
    request: Request,
    *,
    problem_type: str,
    title: str,
    status: int,
    detail: str,
) -> dict[str, Any]:
    """Build a RFC 7807 problem detail payload.

    Args:
        request: Current HTTP request (optional request_id from state).
        problem_type: Short slug appended to the problem base URL.
        title: Short human-readable summary of the problem type.
        status: HTTP status code for this problem.
        detail: Human-readable explanation specific to this occurrence.

    Returns:
        dict[str, Any]: Problem detail body ready for JSON encoding.
    """
    body: dict[str, Any] = {
        "type": f"{PROBLEM_BASE_URL}{problem_type}",
        "title": title,
        "status": status,
        "detail": detail,
    }
    request_id = getattr(request.state, "request_id", None)
    if request_id is not None:
        body["request_id"] = request_id
    return body


def problem_response(
    request: Request,
    *,
    problem_type: str,
    title: str,
    status: int,
    detail: str,
) -> JSONResponse:
    """Return an RFC 7807 JSON response for an application error.

    Args:
        request: Current HTTP request.
        problem_type: Short slug appended to the problem base URL.
        title: Short human-readable summary of the problem type.
        status: HTTP status code for this problem.
        detail: Human-readable explanation specific to this occurrence.

    Returns:
        JSONResponse: Response with `application/problem+json` content type.
    """
    return JSONResponse(
        status_code=status,
        content=build_problem_body(
            request,
            problem_type=problem_type,
            title=title,
            status=status,
            detail=detail,
        ),
        media_type="application/problem+json",
    )


async def handle_location_validation_error(
    request: Request,
    exc: LocationValidationError,
) -> JSONResponse:
    """Map domain location validation failures to 422 problem details."""
    return problem_response(
        request,
        problem_type="invalid-location",
        title="Invalid location query",
        status=422,
        detail=exc.message,
    )


async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Map FastAPI request validation failures to 422 problem details."""
    _ = exc
    return problem_response(
        request,
        problem_type="invalid-location",
        title="Invalid location query",
        status=422,
        detail=_GENERIC_VALIDATION_DETAIL,
    )


async def handle_unhandled_exception(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Map unexpected exceptions to generic 500 problem details."""
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    _ERROR_LOGGER.exception("Unhandled exception", exc_info=exc)
    return problem_response(
        request,
        problem_type="internal-error",
        title="Internal server error",
        status=500,
        detail=_GENERIC_INTERNAL_DETAIL,
    )


async def handle_location_not_found_error(
    request: Request,
    exc: LocationNotFoundError,
) -> JSONResponse:
    """Map upstream location-not-found failures to 404 problem details."""
    return problem_response(
        request,
        problem_type="location-not-found",
        title="Location not found",
        status=404,
        detail=exc.message,
    )


async def handle_upstream_weather_error(
    request: Request,
    exc: UpstreamWeatherError,
) -> JSONResponse:
    """Map upstream weather failures to 502 problem details."""
    return problem_response(
        request,
        problem_type="upstream-weather-error",
        title="Upstream weather service error",
        status=502,
        detail=exc.message,
    )


async def handle_upstream_rate_limit_error(
    request: Request,
    exc: UpstreamRateLimitError,
) -> JSONResponse:
    """Map upstream rate-limit failures to 503 problem details."""
    return problem_response(
        request,
        problem_type="upstream-weather-unavailable",
        title="Upstream weather service unavailable",
        status=503,
        detail=exc.message,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register RFC 7807 handlers on the FastAPI application."""

    @app.exception_handler(LocationValidationError)
    async def location_validation_handler(
        request: Request,
        exc: LocationValidationError,
    ) -> JSONResponse:
        return await handle_location_validation_error(request, exc)

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return await handle_request_validation_error(request, exc)

    @app.exception_handler(LocationNotFoundError)
    async def location_not_found_handler(
        request: Request,
        exc: LocationNotFoundError,
    ) -> JSONResponse:
        return await handle_location_not_found_error(request, exc)

    @app.exception_handler(UpstreamWeatherError)
    async def upstream_weather_handler(
        request: Request,
        exc: UpstreamWeatherError,
    ) -> JSONResponse:
        return await handle_upstream_weather_error(request, exc)

    @app.exception_handler(UpstreamRateLimitError)
    async def upstream_rate_limit_handler(
        request: Request,
        exc: UpstreamRateLimitError,
    ) -> JSONResponse:
        return await handle_upstream_rate_limit_error(request, exc)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        return await handle_unhandled_exception(request, exc)
