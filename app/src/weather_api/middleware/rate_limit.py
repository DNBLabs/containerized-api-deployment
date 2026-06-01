"""In-memory per-client rate limiting for public API routes."""

import time
from collections import defaultdict, deque
from collections.abc import MutableMapping

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from weather_api.config import Settings
from weather_api.errors import build_problem_body

TimestampWindow = deque[float]
RateLimitStore = MutableMapping[str, TimestampWindow]


def default_is_health_path(path: str) -> bool:
    """Return True when the path is a health probe endpoint."""
    return path.startswith("/health/")


def resolve_client_ip(request: Request) -> str:
    """Resolve the best-effort client IP, honoring X-Forwarded-For when present."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def create_rate_limit_store() -> RateLimitStore:
    """Create an empty in-memory store for per-client request timestamps."""
    return defaultdict(deque)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limit request volume per client IP within a sliding time window."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Reject over-limit clients before invoking downstream handlers."""
        if default_is_health_path(request.url.path):
            return await call_next(request)

        settings: Settings = request.app.state.settings
        store: RateLimitStore = request.app.state.rate_limit_store
        client_ip = resolve_client_ip(request)
        now = time.monotonic()
        window = store[client_ip]
        _prune_window(window, now, settings.rate_limit_window_seconds)

        if len(window) >= settings.rate_limit_max_requests:
            return _rate_limit_response(request, settings.rate_limit_window_seconds)

        window.append(now)
        return await call_next(request)


def _prune_window(window: TimestampWindow, now: float, window_seconds: int) -> None:
    """Drop timestamps that fall outside the active window."""
    cutoff = now - window_seconds
    while window and window[0] <= cutoff:
        window.popleft()


def _rate_limit_response(request: Request, retry_after_seconds: int) -> JSONResponse:
    """Build a RFC 7807 429 response for client-side rate limiting."""
    body = build_problem_body(
        request,
        problem_type="rate-limit-exceeded",
        title="Too many requests",
        status=429,
        detail="Rate limit exceeded. Try again later.",
    )
    return JSONResponse(
        status_code=429,
        content=body,
        media_type="application/problem+json",
        headers={"Retry-After": str(retry_after_seconds)},
    )
