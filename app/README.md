# Weather API

Tracer FastAPI service for the containerized deployment reference implementation.

## Local development

```bash
cd app
uv sync
cp ../.env.example ../.env
uv run uvicorn weather_api.main:create_app --factory --host 0.0.0.0 --port 8000
```

Run with **`debug=False`** (default in `create_app`). Do not enable FastAPI debug mode in production.

## Environment variables

See [`.env.example`](../.env.example) at the repository root.

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | HTTP listen port |
| `WEATHER_PROVIDER` | `mock` | `mock` or `openweathermap` |
| `OPENWEATHERMAP_API_KEY` | unset | Required when `WEATHER_PROVIDER=openweathermap` |
| `RATE_LIMIT_MAX_REQUESTS` | `60` | Max weather/API requests per client IP per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit sliding window |
| `ENABLE_HSTS` | `false` | Set `true` behind HTTPS in production (ACA) |

Health probes (`/health/*`) are exempt from rate limiting.

**Rate limit client IP:** Uses `X-Forwarded-For` (first hop) when present, else direct client IP. Trust that header only when the app sits behind a trusted reverse proxy (Azure ACA ingress in production). Direct local exposure allows header spoofing.

## Tests

```bash
cd app
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run bandit -r src/weather_api
```
