"""Health probe routes for liveness and readiness checks."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from weather_api.config import Settings
from weather_api.dependencies import SettingsDep

router = APIRouter(tags=["health"])


def evaluate_readiness(settings: Settings) -> tuple[bool, str | None]:
    """Determine whether the application is ready to serve traffic.

    Args:
        settings: Current runtime settings.

    Returns:
        tuple[bool, str | None]: Ready flag and optional not-ready reason slug.
    """
    if settings.weather_provider == "openweathermap" and not settings.openweathermap_api_key:
        return False, "missing_openweathermap_api_key"
    return True, None


@router.get("/health/live")
def health_live() -> dict[str, str]:
    """Return liveness status when the process is running."""
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready(settings: SettingsDep) -> JSONResponse:
    """Return readiness status based on required configuration."""
    is_ready, reason = evaluate_readiness(settings)

    if is_ready:
        return JSONResponse(status_code=200, content={"status": "ready"})

    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "reason": reason},
    )
