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

## Container image (Task 12)

Build context is **`app/`** (not the monorepo root). From the repository root:

```bash
docker build -t weather-api:local ./app
docker run --rm -p 8000:8000 -e WEATHER_PROVIDER=mock weather-api:local
```

Verify non-root user: `docker run --rm weather-api:local whoami` → `appuser`.

Smoke from the host (with the container running):

```bash
curl -s http://127.0.0.1:8000/health/live
curl -s "http://127.0.0.1:8000/weather?city=London"
```

Docker integration tests (skipped when Docker is unavailable):

```bash
cd app
uv run pytest tests/test_docker_image.py
```

## Tests

```bash
cd app
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run bandit -r src/weather_api
```
