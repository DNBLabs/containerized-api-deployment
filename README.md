# Containerized API Deployment

Reference implementation: tracer weather API, hardened container, Terraform on Azure, GitHub Actions CI/CD.

## Quickstart (Docker Compose)

Primary local path — mock weather, no secrets:

```bash
docker compose up --build
```

```bash
curl -s http://127.0.0.1:8000/health/live
curl -s "http://127.0.0.1:8000/weather?city=London"
```

## Optional: native Python

Fast iteration without Docker — see [`app/README.md`](app/README.md).

## Docs

- [`CONTEXT.md`](CONTEXT.md) — domain glossary
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — task tracker
- [`docs/PRD.md`](docs/PRD.md) — product requirements
