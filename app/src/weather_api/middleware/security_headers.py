"""Security response headers for HTTP hardening."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from weather_api.config import Settings

_STRICT_CONTENT_SECURITY_POLICY = "default-src 'none'; frame-ancestors 'none'"
_DOCS_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.jsdelivr.net; "
    "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)
_DOCS_PATH_PREFIXES = ("/docs", "/redoc", "/openapi.json")


def resolve_content_security_policy(request_path: str) -> str:
    """Return a CSP appropriate for API responses or interactive OpenAPI pages.

    Args:
        request_path: Request path from the incoming HTTP request.

    Returns:
        str: Content-Security-Policy header value for the response.
    """
    if request_path == "/openapi.json" or request_path.startswith(_DOCS_PATH_PREFIXES):
        return _DOCS_CONTENT_SECURITY_POLICY
    return _STRICT_CONTENT_SECURITY_POLICY


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
        response.headers["Content-Security-Policy"] = resolve_content_security_policy(
            request.url.path,
        )
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
