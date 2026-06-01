"""FastAPI application factory for the weather tracer API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from weather_api.application_resources import create_application_resources
from weather_api.config import load_settings
from weather_api.errors import register_exception_handlers
from weather_api.middleware.logging import StructuredLoggingMiddleware
from weather_api.middleware.rate_limit import RateLimitMiddleware, create_rate_limit_store
from weather_api.middleware.request_id import RequestIdMiddleware
from weather_api.middleware.security_headers import SecurityHeadersMiddleware
from weather_api.routes.health import router as health_router
from weather_api.routes.weather import router as weather_router


@asynccontextmanager
async def _app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown resources for the application."""
    yield
    for shutdown_callback in app.state.shutdown_callbacks:
        shutdown_callback()


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application instance.

    Returns:
        FastAPI: Application with routes and middleware registered.
    """
    settings = load_settings()
    resources = create_application_resources(settings)
    app = FastAPI(
        title="Weather API",
        version="0.1.0",
        debug=False,
        lifespan=_app_lifespan,
    )
    app.state.settings = settings
    app.state.weather_provider = resources.weather_provider
    app.state.shutdown_callbacks = resources.shutdown_callbacks
    app.state.rate_limit_store = create_rate_limit_store()
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(weather_router)
    return app
