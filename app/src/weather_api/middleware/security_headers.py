"""Security response headers for HTTP hardening."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from weather_api.config import Settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security headers to every HTTP response."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Apply security headers after the downstream handler returns."""
        settings: Settings = request.app.state.settings
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        if _should_send_hsts(request, settings.enable_hsts):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


def _should_send_hsts(request: Request, enable_hsts: bool) -> bool:
    """Return True when HSTS is enabled and the client request was HTTPS."""
    if not enable_hsts:
        return False
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "").lower()
    return request.url.scheme == "https" or forwarded_proto == "https"
