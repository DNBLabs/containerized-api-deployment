# Implementation Plan: Containerized API Deployment (v1)

**Sources:** [`CONTEXT.md`](CONTEXT.md), [`docs/PRD.md`](docs/PRD.md), [ADR 0001](docs/adr/0001-terraform-remote-state-bootstrap.md)  
**Tracker:** [GitHub Issue #1](https://github.com/DNBLabs/containerized-api-deployment/issues/1)  
**Repo:** [DNBLabs/containerized-api-deployment](https://github.com/DNBLabs/containerized-api-deployment)

## Overview

Build a **reference implementation + production-grade** monorepo: FastAPI **tracer API** (weather), hardened **Docker** image, **Terraform** on Azure (`uksouth`, ACA/ACR/Key Vault), and **GitHub Actions** (OIDC, SHA tags, quality gates). Each phase leaves the repo in a **working, verifiable** state. Work is **vertically sliced** inside the app phase so early tasks already deliver testable HTTP behavior.

## Dependency Graph

```
[Task 1: App scaffold]
        │
        ├── [Task 2: Domain models]
        ├── [Task 3: Location validation + tests]
        ├── [Task 4: Mock provider + tests]
        │         │
        │         └── [Task 5: GET /weather + tests]  ← first vertical slice
        ├── [Task 6: RFC 7807 handlers]
        ├── [Task 7: X-Request-ID middleware]
        ├── [Task 8: JSON logging middleware]
        ├── [Task 9: Health endpoints + tests]
        └── [Task 10: OpenWeatherMap provider + tests]
                  │
                  └── [Task 11: Provider factory + app wiring]

── Checkpoint A: local API complete ──

[Task 12: Dockerfile]
[Task 13: Compose + .dockerignore]

── Checkpoint B: containerized local API ──

[Task 14: Bootstrap Terraform]  (ADR 0001, manual apply)
[Task 15: Main TF backend + variables]
[Task 16: RG + ACR + Key Vault]
[Task 17: ACA environment + container app skeleton]
[Task 18: Runtime MI AcrPull + app env/secrets/KV refs]
[Task 19: GitHub UAMI + OIDC + RG RBAC]

── Checkpoint C: Azure infra provisioned (manual KV secret) ──

[Task 20: CI — test/lint/mypy workflow]
[Task 21: CI — build, Trivy, push ACR]
[Task 22: CI — deploy ACA revision on main]
[Task 23: CI — infra fmt/validate/plan/apply path-filter]

── Checkpoint D: pipeline green on main ──

[Task 24: README + Mermaid + Day-0/2 ops]

── Checkpoint E: v1 complete ──
```

## Architecture Decisions (from design — do not re-litigate in tasks)

- **Monorepo:** `app/`, `infra/`, `infra/bootstrap/`, `.github/workflows/`
- **`WEATHER_PROVIDER`:** `mock` | `openweathermap`; prod uses latter; CI/Compose default `mock`
- **Images:** `weather-api:<7-char-sha>` only; no `latest` for deploys
- **Terraform:** bootstrap local state (gitignored); main stack remote state; apply in CI only when `infra/**` changes
- **Secrets:** `OPENWEATHERMAP_API_KEY` in Key Vault via manual one-shot; OIDC for CI (no `AZURE_CREDENTIALS`)
- **ACA:** `minReplicas=1`, `maxReplicas=3`; public default FQDN; system-assigned MI → AcrPull

## Parallelization

| Parallel safe (after deps) | Must be sequential |
|----------------------------|-------------------|
| Tasks 6–9 after Task 5 (orthogonal middleware) | 1 → 2–4 → 5 → 11 |
| Task 10 after Task 2 (OWM provider) | 14 before 15–19 |
| Tasks 20–23 after Checkpoint C | Bootstrap before main backend config |

---

## Task List

### Phase 1: Tracer API (local, testable)

**Progress (2025-06-01, Phase 1 complete):** Tasks **1–11** complete. **37 tests** pass. **Checkpoint A** complete (human review passed). Architecture slices 1–4 applied. **Task 20** app CI workflow added (`.github/workflows/ci.yml`).

---

## Task 1: Application scaffold (`uv` + FastAPI shell)

**Description:** Create `app/` Python package with `pyproject.toml`, `uv.lock`, Python 3.12 pin, FastAPI app factory, and empty router mount. Add dev deps: pytest, pytest-asyncio (if async), httpx, ruff, mypy.

**Acceptance criteria:**
- [x] `uv sync` succeeds from repo root
- [x] `uv run uvicorn` starts app on configured port (e.g. 8000)
- [x] `GET /` or root returns 404 or minimal health stub (not required final contract)

**Verification:**
- [x] `cd app && uv run ruff check .`
- [x] `cd app && uv run mypy .` (strict per Phase Lock [1])
- [x] Manual: server starts without error

**Dependencies:** None

**Files likely touched:**
- `app/pyproject.toml`, `app/uv.lock`, `app/src/.../main.py`, `app/src/.../__init__.py`

**Estimated scope:** Small (2–4 files)

---

## Task 2: Domain models (`Location`, `WeatherSummary`)

**Description:** Pydantic models for normalized weather response and location input types used across providers and API layer.

**Acceptance criteria:**
- [x] `WeatherSummary` fields match CONTEXT: `location`, `temperature_c`, `conditions`, `humidity_percent`, `wind_speed_mps`, `provider`, `observed_at`
- [x] `Location` supports city OR lat/lon representation (`CityLocation` \| `CoordinateLocation` discriminated union)

**Verification:**
- [x] Unit tests serialize/deserialize sample JSON
- [x] `uv run pytest` passes for model tests

**Dependencies:** Task 1

**Files likely touched:**
- `app/src/.../models.py`, `app/tests/test_models.py`

**Estimated scope:** XS (1–2 files)

---

## Task 3: Location validation (city XOR lat/lon)

**Description:** Deep module: `parse_location_query(city, lat, lon) -> Location` raising domain validation errors for both/neither/invalid ranges.

**Acceptance criteria:**
- [x] city-only → valid `Location`
- [x] lat+lon only → valid `Location`
- [x] both city and coordinates → validation error
- [x] neither → validation error
- [x] out-of-range lat/lon → validation error

**Verification:**
- [x] `uv run pytest app/tests/test_location.py` (or equivalent path)

**Dependencies:** Task 2

**Files likely touched:**
- `app/src/.../location.py`, `app/tests/test_location.py`

**Estimated scope:** XS

---

## Task 4: Mock weather provider

**Description:** Deterministic `MockWeatherProvider` implementing `get_current_weather(location) -> WeatherSummary` with `provider="mock"`.

**Acceptance criteria:**
- [x] Same location input yields stable output across calls
- [x] Output passes `WeatherSummary` validation

**Verification:**
- [x] `uv run pytest` for mock provider tests

**Dependencies:** Task 2

**Files likely touched:**
- `app/src/.../providers/mock.py`, `app/tests/test_mock_provider.py`

**Estimated scope:** XS

---

## Task 5: `GET /weather` vertical slice (mock only)

**Description:** Wire FastAPI route `GET /weather` using location validation + mock provider (hardcode or env default `mock`). Return normalized JSON.

**Acceptance criteria:**
- [x] `?city=London` returns 200 + `WeatherSummary` JSON
- [x] `?lat=51.5&lon=-0.12` returns 200
- [x] Invalid combinations return 4xx (problem+json if Task 6 done; else JSON error until Task 6)

**Verification:**
- [x] `uv run pytest` integration tests with `TestClient`
- [x] Manual `curl` local server *(city + coords verified via tests)*

**Dependencies:** Tasks 3, 4

**Files likely touched:**
- `app/src/.../routes/weather.py`, `app/src/.../main.py`, `app/tests/test_weather_api.py`

**Estimated scope:** Small

---

## Task 6: RFC 7807 problem details

**Description:** Exception handlers mapping validation, upstream, and internal errors to `application/problem+json`; include `request_id` extension when available.

**Acceptance criteria:**
- [x] Validation errors return 422 (or 400 per design) with problem+json body
- [x] `Content-Type` is `application/problem+json` on error responses

**Verification:**
- [x] Tests assert problem structure on bad query params

**Dependencies:** Task 5

**Files likely touched:**
- `app/src/.../errors.py`, `app/src/.../main.py`, `app/tests/test_errors.py`

**Estimated scope:** Small

---

## Task 7: `X-Request-ID` middleware

**Description:** Honor incoming `X-Request-ID` or generate UUID; attach to request state; echo on responses.

**Acceptance criteria:**
- [x] Client-sent ID returned on response header
- [x] Missing header → new UUID on response

**Verification:**
- [x] `pytest` middleware/route tests

**Dependencies:** Task 5

**Files likely touched:**
- `app/src/.../middleware/request_id.py`, tests

**Estimated scope:** XS

---

## Task 8: Structured JSON logging

**Description:** Request-scoped JSON log lines to stdout: `timestamp`, `level`, `message`, `request_id`, `path`, `status_code`, `duration_ms`, `provider` (when known).

**Acceptance criteria:**
- [x] One log line per request completion
- [x] `request_id` matches Task 7

**Verification:**
- [x] Test captures log output or tests handler attachment
- [ ] Manual: single request produces parseable JSON line

**Dependencies:** Task 7

**Files likely touched:**
- `app/src/.../middleware/logging.py`, tests

**Estimated scope:** Small

---

## Task 9: Health endpoints (`/health/live`, `/health/ready`)

**Description:** Liveness always 200 if process up. Readiness checks config: if `WEATHER_PROVIDER=openweathermap`, require `OPENWEATHERMAP_API_KEY`; mock mode ready without key. **No** OpenWeatherMap HTTP on ready.

**Acceptance criteria:**
- [x] `/health/live` → 200
- [x] `mock` + no key → `/health/ready` 200
- [x] `openweathermap` + missing key → `/health/ready` 503 (or 503 semantics documented)

**Verification:**
- [x] `uv run pytest` health tests with env overrides

**Dependencies:** Task 1 (config module)

**Files likely touched:**
- `app/src/.../routes/health.py`, `app/src/.../config.py`, tests

**Estimated scope:** Small

---

## Task 10: OpenWeatherMap provider + HTTP client

**Description:** `OpenWeatherMapProvider` with timeouts, maps fixture/upstream JSON to `WeatherSummary`, maps failures to domain errors for problem handlers (502/503).

**Acceptance criteria:**
- [x] Unit tests use httpx mock — **no live network**
- [x] `provider="openweathermap"` in response
- [x] Timeout → appropriate domain error

**Verification:**
- [x] `uv run pytest` provider tests

**Dependencies:** Task 2

**Files likely touched:**
- `app/src/.../providers/openweathermap.py`, `app/src/.../http_client.py`, tests

**Estimated scope:** Small–Medium

---

## Task 11: Provider factory + final app wiring

**Description:** Select provider from `WEATHER_PROVIDER` env; register all routes, middleware, handlers; enable `/docs`.

**Acceptance criteria:**
- [x] `WEATHER_PROVIDER=mock` → mock backend
- [x] `WEATHER_PROVIDER=openweathermap` + key → OWM backend (local manual test optional)
- [x] `/docs` returns 200

**Verification:**
- [x] Full `uv run pytest`
- [x] `uv run ruff check . && uv run ruff format --check .`
- [x] `uv run mypy .`

**Dependencies:** Tasks 5–10

**Files likely touched:**
- `app/src/.../providers/factory.py`, `app/src/.../main.py`, `app/README.md` (env vars)

**Estimated scope:** Small

---

### Checkpoint A: Local tracer API complete

- [x] `cd app && uv run pytest` *(37 tests)*
- [x] `cd app && uv run ruff check . && uv run ruff format --check .`
- [x] `cd app && uv run mypy .`
- [x] `curl` `/weather`, `/health/live`, `/health/ready`, `/docs` locally with `WEATHER_PROVIDER=mock`
- [x] **Human review** before Phase 2 *(smoke, CONTEXT contract, CI green — passed)*

---

### Phase 2: Containerization

**Phase Lock [2] (2025-06-02):** Decisions locked in `CONTEXT.md` — `app/Dockerfile`, multi-stage `uv` builder, `appuser` (10001), exec CMD port 8000, root `compose.yml` with inline mock env, compose-only healthcheck, production `.dockerignore`, cache-friendly COPY layers, `restart: unless-stopped`.

---

## Task 12: Production Dockerfile (non-root, slim)

**Description:** Multi-stage or slim `python:3.12` image; install from `uv.lock`; non-root user; `EXPOSE` app port; `CMD` uvicorn.

**Acceptance criteria:**
- [x] Image builds successfully — `app/Dockerfile` multi-stage; integration test `test_production_docker_image_builds`
- [x] Container runs as non-root (`docker run` + `whoami` or image USER) — `appuser` UID/GID 10001; test `test_production_container_runs_as_appuser`
- [x] Health/weather reachable inside container — tests `test_production_container_serves_health_live`, `test_production_container_serves_weather_with_mock_provider`

**Verification:**
- [x] `docker build -t weather-api:local ./app` (documented in `app/README.md`; run locally when Docker available)
- [x] `docker run` + `curl` localhost mapped port (documented; covered by integration tests when Docker available)

**Dependencies:** Checkpoint A

**Files likely touched:**
- `app/Dockerfile` or root `Dockerfile` (document choice in README)

**Estimated scope:** Small

---

## Task 13: Docker Compose (mock default)

**Description:** Root `compose.yml`: build app, `WEATHER_PROVIDER=mock`, port map, no secrets required.

**Acceptance criteria:**
- [ ] `docker compose up --build` starts API
- [ ] `GET /weather?city=London` works from host

**Verification:**
- [ ] `docker compose up -d && curl ...`

**Dependencies:** Task 12

**Files likely touched:**
- `compose.yml`, `.dockerignore`

**Estimated scope:** XS

---

### Checkpoint B: Containerized local API

- [ ] `docker compose up --build` + curl weather/health
- [ ] Document optional `uv run` path in `app/README.md` or root README stub

---

### Phase 3: Infrastructure (Terraform)

---

## Task 14: Bootstrap stack (`infra/bootstrap/`)

**Description:** Per ADR 0001: storage account + container for TF state; outputs for backend config; gitignore local `*.tfstate*`.

**Acceptance criteria:**
- [ ] `terraform init && terraform apply` succeeds (operator, `uksouth`)
- [ ] Outputs document backend storage account/container names

**Verification:**
- [ ] `terraform validate` in bootstrap dir
- [ ] Manual apply in personal subscription (documented, not CI)

**Dependencies:** None (Day-0; can parallelize with Phase 1–2 in separate session)

**Files likely touched:**
- `infra/bootstrap/*.tf`, `infra/bootstrap/README.md`, `.gitignore`

**Estimated scope:** Small–Medium

---

## Task 15: Main stack skeleton + remote backend

**Description:** `infra/envs/prod/` (or `infra/prod/`) with `azurerm` backend block pointing at bootstrap outputs; variables for location, prefix `cad`, tags.

**Acceptance criteria:**
- [ ] `terraform init` succeeds after bootstrap
- [ ] `terraform validate` passes

**Verification:**
- [ ] `terraform validate` in main stack

**Dependencies:** Task 14

**Files likely touched:**
- `infra/envs/prod/backend.tf`, `versions.tf`, `variables.tf`

**Estimated scope:** Small

---

## Task 16: Core Azure resources (RG, ACR, Key Vault)

**Description:** `rg-cad-prod-uksouth`, `acrcadprod`, `kv-cad-prod-uks` with RBAC-ready structure; KV for secrets (no OWM value in TF).

**Acceptance criteria:**
- [ ] `terraform plan` shows three resource groups of resources without error
- [ ] Naming matches CONTEXT

**Verification:**
- [ ] `terraform plan` (local, after bootstrap)

**Dependencies:** Task 15

**Files likely touched:**
- `infra/envs/prod/main.tf`, `acr.tf`, `keyvault.tf`

**Estimated scope:** Medium

---

## Task 17: ACA environment + container app

**Description:** `cae-cad-prod-uksouth`, `ca-weather-api-prod`, public ingress, `minReplicas=1`, `maxReplicas=3`, probes pointing to `/health/live` and `/health/ready`.

**Acceptance criteria:**
- [ ] Plan includes ACA env + app with ingress FQDN output
- [ ] Probe paths match app routes

**Verification:**
- [ ] `terraform plan` review

**Dependencies:** Task 16

**Files likely touched:**
- `infra/envs/prod/aca.tf`, `outputs.tf`

**Estimated scope:** Medium

---

## Task 18: Runtime identity + ACA secrets wiring

**Description:** System-assigned MI on container app; `AcrPull` on ACR; ACA env `WEATHER_PROVIDER=openweathermap`; secret ref `OPENWEATHERMAP_API_KEY` from Key Vault (secret must exist — manual step).

**Acceptance criteria:**
- [ ] No ACR admin user
- [ ] Container app template references KV secret name `OPENWEATHERMAP_API_KEY`

**Verification:**
- [ ] `terraform apply` (local) + portal check identities
- [ ] Manual: `az keyvault secret set` documented; ready probe passes after secret set

**Dependencies:** Task 17

**Files likely touched:**
- `infra/envs/prod/aca.tf`, `rbac.tf`

**Estimated scope:** Small–Medium

---

## Task 19: GitHub OIDC identity + RBAC

**Description:** `id-cad-github-prod`, federated credential for `repo:DNBLabs/containerized-api-deployment:ref:refs/heads/main`, role assignments on `rg-cad-prod-uksouth` (Contributor or documented subset).

**Acceptance criteria:**
- [ ] No client secret outputs in Terraform
- [ ] Federated subject matches repo + `main` only

**Verification:**
- [ ] `terraform plan` shows UAMI + federated credential + role assignment

**Dependencies:** Task 16

**Files likely touched:**
- `infra/envs/prod/github_oidc.tf`, `rbac.tf`

**Estimated scope:** Medium

---

### Checkpoint C: Azure infrastructure

- [ ] Bootstrap applied; main stack applied
- [ ] `az keyvault secret set` for `OPENWEATHERMAP_API_KEY` completed
- [ ] ACA FQDN exists (app image may be placeholder until Phase 4)
- [ ] **Human:** confirm subscription cost acceptable

---

### Phase 4: CI/CD

---

## Task 20: CI workflow — test, ruff, mypy (PR + main)

**Description:** `.github/workflows/ci.yml`: on PR and push to `main`, run from `app/` with `WEATHER_PROVIDER=mock`.

**Acceptance criteria:**
- [x] Workflow runs pytest, ruff check, ruff format --check, mypy
- [x] Fails on test/lint/type errors

**Verification:**
- [ ] Open PR; checks appear on GitHub *(requires push to remote)*

**Dependencies:** Checkpoint A

**Files likely touched:**
- `.github/workflows/ci.yml`

**Estimated scope:** Small

---

## Task 21: CI workflow — build, Trivy, push ACR

**Description:** On `main`, OIDC login, build image, tag `:${{ github.sha }}` shortened to 7 chars, push to `acrcadprod`, Trivy fail on Critical.

**Acceptance criteria:**
- [ ] Image in ACR with 7-char SHA tag only
- [ ] Critical CVE fails pipeline

**Verification:**
- [ ] Merge to `main`; verify ACR tag

**Dependencies:** Checkpoint C, Task 12, Task 19

**Files likely touched:**
- `.github/workflows/deploy-app.yml` (or combined workflow)

**Estimated scope:** Medium

---

## Task 22: CI workflow — deploy ACA revision

**Description:** After push, update `ca-weather-api-prod` to new image tag via Azure CLI or ARM/az action; rolling revision.

**Acceptance criteria:**
- [ ] Live FQDN serves new revision after `main` merge
- [ ] `GET /weather` returns real OWM data when secret present

**Verification:**
- [ ] `curl` production `/weather?city=London`
- [ ] `/docs` loads

**Dependencies:** Task 21

**Files likely touched:**
- `.github/workflows/deploy-app.yml`

**Estimated scope:** Small

---

## Task 23: CI workflow — Terraform path-filtered

**Description:** On PR touching `infra/**`: fmt, validate, plan. On `main` + `infra/**` changes: OIDC + apply.

**Acceptance criteria:**
- [ ] PR with only `app/` changes does not run `terraform apply`
- [ ] PR with `infra/` changes shows plan output

**Verification:**
- [ ] Test PRs: app-only vs infra touch

**Dependencies:** Checkpoint C, Task 19

**Files likely touched:**
- `.github/workflows/infra.yml`

**Estimated scope:** Small

---

### Checkpoint D: Pipeline end-to-end

- [ ] Branch protection on `main` enabled (required checks)
- [ ] Green run: test → build → scan → push → deploy
- [ ] Live HTTPS weather + docs

---

### Phase 5: Documentation & v1 sign-off

---

## Task 24: README + architecture + operations

**Description:** Root README: quickstart (Compose), architecture Mermaid (GitHub → Actions → ACR → ACA → OWM), Day-0 bootstrap, KV secret, OIDC prerequisites, live URL, rollback-by-SHA, cost/teardown, link ADR 0001 + CONTEXT + PRD.

**Acceptance criteria:**
- [ ] New contributor can follow README to local run without Azure
- [ ] Operator can follow Day-0/Day-1 to prod
- [ ] Mermaid renders on GitHub

**Verification:**
- [ ] Human read-through
- [ ] Links valid

**Dependencies:** Checkpoints B–D

**Files likely touched:**
- `README.md`, optional `docs/architecture.md`

**Estimated scope:** Medium

---

### Checkpoint E: v1 complete

- [ ] All PRD user stories satisfied or explicitly deferred in CONTEXT
- [ ] Issue #1 acceptance: reviewer can clone, run Compose, see green CI, hit prod URL
- [ ] `CONTEXT.md` unchanged terms; update only if implementation revealed glossary gaps
- [ ] Ready for human review / portfolio publish

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| ACR name `acrcadprod` globally taken | High | Plan early; add suffix variable if apply fails |
| Bootstrap state lost on laptop | Med | ADR 0001 mitigations; backup tfstate note in README |
| OWM rate limits / key missing | Med | Mock in CI; clear ready probe; README secret step |
| RG Contributor too broad for OIDC | Low (v1) | Document future ADR to tighten roles |
| ACA + KV RBAC propagation delay | Med | Retry ready check in README after secret set |
| Trivy false positives block deploy | Med | Pin base image; document exception process (no bypass in v1 unless needed) |

## Open Questions

- [ ] **GitHub org/repo subject:** Confirm `DNBLabs/containerized-api-deployment` matches actual federated credential (if repo renamed, update TF).
- [ ] **Contributor vs custom roles:** Accept RG Contributor for v1 or tighten before Task 19?
- [x] **Dockerfile location:** **`app/Dockerfile`** + root **`compose.yml`** with `build.context: ./app` — Phase Lock [2], Option A.

## Suggested Session Boundaries (for agents)

| Session | Tasks | Goal |
|---------|-------|------|
| 1 | 1–5 | Mock weather API callable |
| 2 | 6–11 | Full local API + quality tools |
| 3 | 12–13 | Docker/Compose |
| 4 | 14–19 | Azure infra (operator apply) |
| 5 | 20–23 | CI/CD |
| 6 | 24 | Docs + v1 sign-off |

---

## Plan Approval

- [ ] Human reviewed and approved this plan before implementation starts

*Update checkboxes in this file as tasks complete (per project checklist protocol).*
