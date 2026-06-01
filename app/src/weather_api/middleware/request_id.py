"""Middleware for propagating X-Request-ID across requests and responses."""

import re
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
_MAX_REQUEST_ID_LENGTH = 128
_PRINTABLE_ASCII_PATTERN = re.compile(r"^[\x20-\x7E]+$")


def resolve_request_id(header_value: str | None) -> str:
    """Accept a valid client request ID or generate a new UUID.

    Args:
        header_value: Raw X-Request-ID header value from the client, if any.

    Returns:
        str: Request ID to use for correlation in logs and responses.
    """
    if header_value is None:
        return str(uuid.uuid4())

    trimmed = header_value.strip()
    if not trimmed or trimmed.isspace():
        return str(uuid.uuid4())

    if len(trimmed) > _MAX_REQUEST_ID_LENGTH:
        return str(uuid.uuid4())

    if _PRINTABLE_ASCII_PATTERN.fullmatch(trimmed) is None:
        return str(uuid.uuid4())

    return trimmed


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a request ID to request state and response headers."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Resolve, store, and echo X-Request-ID for the request lifecycle."""
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
