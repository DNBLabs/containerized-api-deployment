"""Structured JSON request logging middleware."""

import json
import logging
import time
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_LOGGER_NAME = "weather_api.request"


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Emit one JSON log line per completed HTTP request."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Log request completion with correlation and timing metadata."""
        logger = logging.getLogger(REQUEST_LOGGER_NAME)
        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

        provider = getattr(request.state, "weather_provider", None)
        log_payload = {
            "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            "level": "INFO",
            "message": "request completed",
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "provider": provider,
        }
        logger.info(json.dumps(log_payload))
        return response
