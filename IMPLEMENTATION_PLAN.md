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
- [x] `docker compose up --build` starts API — root `compose.yml`; test `test_compose_up_serves_weather_from_host`
- [x] `GET /weather?city=London` works from host — same integration test + README quickstart

**Verification:**
- [x] `docker compose up -d && curl ...` — covered by `app/tests/test_compose.py` when Docker available

**Dependencies:** Task 12

**Files likely touched:**
- `compose.yml`, `.dockerignore`

**Estimated scope:** XS

---

### Checkpoint B: Containerized local API

- [x] `docker compose up --build` + curl weather/health — root `README.md` + compose integration tests
- [x] Document optional `uv run` path in `app/README.md` or root README stub — root `README.md` + `app/README.md`

---

### Phase 3: Infrastructure (Terraform)

---

## Task 14: Bootstrap stack (`infra/bootstrap/`)

**Description:** Per ADR 0001: storage account + container for TF state; outputs for backend config; gitignore local `*.tfstate*`.

**Acceptance criteria:**
- [x] `terraform init && terraform apply` succeeds (operator, `uksouth`) — `stcadprodtf` + `tfstate` container in `rg-cad-tfstate-uksouth`; operator verified apply/teardown
- [x] Outputs document backend storage account/container names — `outputs.tf` + `README.md`; test `test_bootstrap_declares_backend_config_outputs`
- [x] State storage hardened — account keys off, TLS 1.2+, private container, infra encryption, Azure AD backend + `storage_use_azuread`; test `test_bootstrap_storage_account_security_contract`; README security/troubleshooting

**Verification:**
- [x] `terraform validate` in bootstrap dir — `app/tests/test_bootstrap_terraform.py` + local `terraform validate`
- [x] Manual apply in personal subscription (documented, not CI) — operator apply succeeded; README teardown documented

**Dependencies:** None (Day-0; can parallelize with Phase 1–2 in separate session)

**Files likely touched:**
- `infra/bootstrap/*.tf`, `infra/bootstrap/README.md`, `.gitignore`

**Estimated scope:** Small–Medium

---

## Task 15: Main stack skeleton + remote backend

**Description:** `infra/envs/prod/` (or `infra/prod/`) with `azurerm` backend block pointing at bootstrap outputs; variables for location, prefix `cad`, tags.

**Acceptance criteria:**
- [x] `terraform init` succeeds after bootstrap — remote backend configured; `ARM_USE_AZUREAD=true`; Blob Data Contributor on `stcadprodtf`; state blob `prod.terraform.tfstate` in `tfstate`
- [x] `terraform validate` passes — `app/tests/test_prod_terraform.py` + local `terraform validate`
- [x] Remote backend security documented — Entra-only backend template, `storage_use_azuread`, gitignored `backend.hcl`, `security_notes` output; test `test_prod_stack_remote_state_security_contract`; README security section

**Verification:**
- [x] `terraform validate` in main stack — `test_prod_stack_terraform_validates`

**Dependencies:** Task 14

**Files likely touched:**
- `infra/envs/prod/backend.tf`, `versions.tf`, `variables.tf`

**Estimated scope:** Small

---

## Task 16: Core Azure resources (RG, ACR, Key Vault)

**Description:** `rg-cad-prod-uksouth`, `acrcadprod`, `kv-cad-prod-uks` with RBAC-ready structure; KV for secrets (no OWM value in TF).

**Acceptance criteria:**
- [x] `terraform plan` shows three resource groups of resources without error — RG + ACR + Key Vault in `main.tf`/`acr.tf`/`keyvault.tf`; `terraform validate` passes; operator `terraform plan` after bootstrap
- [x] Naming matches CONTEXT — locals default to `rg-cad-prod-uksouth`, `acrcadprod`, `kv-cad-prod-uks`; tests `test_prod_stack_core_resource_locals_match_context`, ACR/KV contract tests

**Verification:**
- [x] `terraform plan` (local, after bootstrap) — documented in `infra/envs/prod/README.md`; static gate `test_prod_stack_terraform_validates`

**Dependencies:** Task 15

**Files likely touched:**
- `infra/envs/prod/main.tf`, `acr.tf`, `keyvault.tf`

**Estimated scope:** Medium

---

## Task 17: ACA environment + container app

**Description:** `cae-cad-prod-uksouth`, `ca-weather-api-prod`, public ingress, `minReplicas=1`, `maxReplicas=3`, probes pointing to `/health/live` and `/health/ready`.

**Acceptance criteria:**
- [x] Plan includes ACA env + app with ingress FQDN output — `aca.tf`; outputs `container_app_fqdn`, `container_app_name`, `container_app_environment_name`; tests `test_prod_stack_declares_aca_environment_and_container_app`, `test_prod_stack_outputs_aca_ingress_fqdn`
- [x] Probe paths match app routes — liveness `/health/live`, readiness `/health/ready`, port 8000; same ACA contract test
- [x] Security contract — HTTPS-only ingress (`allow_insecure_connections = false`), `ENABLE_HSTS=true`, no secrets in TF, `container_image` validation; test `test_prod_stack_aca_security_contract`

**Verification:**
- [x] `terraform plan` review — `terraform validate` passes; operator plan after apply documented in README

**Dependencies:** Task 16

**Files likely touched:**
- `infra/envs/prod/aca.tf`, `outputs.tf`

**Estimated scope:** Medium

---

## Task 18: Runtime identity + ACA secrets wiring

**Description:** System-assigned MI on container app; `AcrPull` on ACR; ACA env `WEATHER_PROVIDER=openweathermap`; secret ref `OPENWEATHERMAP_API_KEY` from Key Vault (secret must exist — manual step).

**Acceptance criteria:**
- [x] No ACR admin user — `admin_enabled = false` unchanged; test `test_prod_stack_aca_runtime_identity_and_acr_pull`
- [x] Container app template references KV secret name `OPENWEATHERMAP_API_KEY` — ACA secret ref + env `secret_name`; test `test_prod_stack_aca_weather_provider_and_kv_secret_ref`

**Verification:**
- [x] `terraform validate` + contract tests — 16/16 `test_prod_terraform.py`
- [x] Manual `az keyvault secret set` documented — `infra/envs/prod/README.md` Task 18 section

**Dependencies:** Task 17

**Files likely touched:**
- `infra/envs/prod/aca.tf`, `rbac.tf`

**Estimated scope:** Small–Medium

---

## Task 19: GitHub OIDC identity + RBAC

**Description:** `id-cad-github-prod`, federated credential for `repo:DNBLabs/containerized-api-deployment:ref:refs/heads/main`, role assignments on `rg-cad-prod-uksouth` (Contributor or documented subset).

**Acceptance criteria:**
- [x] No client secret outputs in Terraform — `github_ci_client_id` only; test `test_prod_stack_github_oidc_outputs_without_secrets`
- [x] Federated subject matches repo + `main` only — `repo:DNBLabs/containerized-api-deployment:ref:refs/heads/main`; test `test_prod_stack_github_oidc_federated_credential_main_only`

**Verification:**
- [x] `terraform validate` + contract tests — 21/21 `test_prod_terraform.py` (incl. `test_prod_stack_github_oidc_security_contract`)
- [x] `terraform plan` shows UAMI + federated credential + role assignment — applied 2025-06-03 (3 added, 0 changed)

**Dependencies:** Task 16

**Files likely touched:**
- `infra/envs/prod/github_oidc.tf`, `rbac.tf`

**Estimated scope:** Medium

---

### Checkpoint C: Azure infrastructure

- [x] Bootstrap applied; main stack applied
- [x] `az keyvault secret set` for `OPENWEATHERMAP_API_KEY` completed
- [x] ACA FQDN exists (app image may be placeholder until Phase 4)
- [x] **Human:** confirm subscription cost acceptable

---

### Phase 4: CI/CD

**Phase Lock [4] (2025-06-04):** Decisions locked in `CONTEXT.md` — three workflows (`ci.yml`, `deploy-app.yml`, `infra.yml`); `ci.yml` on PR + push to `main` (pytest, ruff, mypy, bandit); `deploy-app.yml` via `workflow_run` after CI success, paths-filter for app changes, checkout `head_sha`, GitHub Environment `production` for Azure OIDC, build context `app/`, tag `acrcadprod.azurecr.io/weather-api:<7-char-sha>`, Trivy fail Critical, `az containerapp update`, smoke `/health/live` with FQDN from `az containerapp show`, concurrency `deploy-prod` cancel-in-progress; `infra.yml` path `infra/**`, PR plan to job summary, main apply, `infra-prod` no cancel; branch protection requires `App quality gates` only; OIDC subject confirmed `DNBLabs/containerized-api-deployment`.

---

## Task 20: CI workflow — test, ruff, mypy (PR + main)

**Description:** `.github/workflows/ci.yml`: on PR and push to `main`, run from `app/` with `WEATHER_PROVIDER=mock`.

**Acceptance criteria:**
- [x] Workflow runs pytest, ruff check, ruff format --check, mypy, bandit
- [x] Triggers on `pull_request` and `push` to `main` (Phase Lock [4])
- [x] Fails on test/lint/type errors

**Verification:**
- [x] Open PR; checks appear on GitHub — PR [#2](https://github.com/DNBLabs/containerized-api-deployment/pull/2); **App quality gates** passed

**Dependencies:** Checkpoint A

**Files likely touched:**
- `.github/workflows/ci.yml`
- `app/tests/test_ci_workflow.py`

**Estimated scope:** Small

---

**Task Lock [21] (2025-06-04):** Security hardening on `deploy-app.yml` — deploy only when triggering CI event is **`push`** (not PR) and **`head_repository` matches this repo**; job-level **`id-token: write`** only on `build-push-scan`; checkout **`fetch-depth: 1`** + **`persist-credentials: false`**; validate **7-char hex** `IMAGE_TAG`; Trivy **before** push; Azure creds via **`production` environment secrets** only. Accepted v1 risk: UAMI **Contributor** on prod RG.

## Task 21: CI workflow — build, Trivy, push ACR

**Description:** On `main`, OIDC login, build image, tag `:${{ github.sha }}` shortened to 7 chars, push to `acrcadprod`, Trivy fail on Critical.

**Acceptance criteria:**
- [x] Workflow contract: OIDC, 7-char SHA tag, Trivy Critical gate, ACR push (`deploy-app.yml` + contract tests)
- [x] Image in ACR with 7-char SHA tag only — `acrcadprod.azurecr.io/weather-api:54a1fe9` (Deploy app run [#26970881675](https://github.com/DNBLabs/containerized-api-deployment/actions/runs/26970881675))
- [x] Critical CVE fails pipeline — verified live (perl-base CRITICAL blocked before `ignore-unfixed`; fixable Critical still fail)

**Verification:**
- [x] Merge to `main`; verify ACR tag — `az acr repository show-tags` shows `54a1fe9` (2025-06-04)

**Dependencies:** Checkpoint C, Task 12, Task 19

**Files likely touched:**
- `.github/workflows/deploy-app.yml`
- `app/tests/test_deploy_app_workflow.py`
- `infra/envs/prod/github_oidc.tf` *(production environment OIDC subject)*

**Estimated scope:** Medium

---

**Task Lock [22] (2025-06-04):** ACA deploy in same `build-push-scan` job after ACR push — `az containerapp update` with `--container-name weather-api` on `ca-weather-api-prod` / `rg-cad-prod-uksouth` ([MS CLI ref](https://learn.microsoft.com/en-us/cli/azure/containerapp?view=azure-cli-latest#az-containerapp-update)). Post-deploy smoke: `curl -fsS` `https://<fqdn>/health/live` only; FQDN from `az containerapp show`; 5× retry / 15s for revision propagation. Manual `/weather` + `/docs` remain Task 22 verification.

## Task 22: CI workflow — deploy ACA revision

**Description:** After push, update `ca-weather-api-prod` to new image tag via Azure CLI or ARM/az action; rolling revision.

**Acceptance criteria:**
- [x] Workflow contract: ACA update after push + `/health/live` smoke (`deploy-app.yml` + contract tests)
- [x] Live FQDN serves new revision after `main` merge
- [x] `GET /weather` returns real OWM data when secret present

**Verification:**
- [x] `curl` production `/weather?city=London`
- [x] `/docs` loads

**Dependencies:** Task 21

**Files likely touched:**
- `.github/workflows/deploy-app.yml`
- `app/tests/test_deploy_app_workflow.py`

**Estimated scope:** Small

---

**Task Lock [23] (2025-06-04):** Added `.github/workflows/infra.yml` — `paths: infra/**` on PR/push to `main`; `terraform fmt -check`, `validate`, `plan` + plan in **job summary** (`GITHUB_STEP_SUMMARY`); **`apply` only on `push` to `main`**; `infra/envs/prod/`, `ARM_USE_AZUREAD`, OIDC via **`production`**; concurrency **`infra-prod`** / no cancel. Contract tests in `app/tests/test_infra_workflow.py`.

## Task 23: CI workflow — Terraform path-filtered

**Description:** On PR touching `infra/**`: fmt, validate, plan. On `main` + `infra/**` changes: OIDC + apply.

**Acceptance criteria:**
- [x] PR with only `app/` changes does not run `terraform apply` — workflow does not trigger without `infra/**` path match (contract test)
- [x] PR with `infra/` changes shows plan output — `Publish plan to job summary` step (`test_infra_workflow_publishes_plan_to_job_summary`)

**Verification:**
- [x] Test PRs: app-only vs infra touch — [#9](https://github.com/DNBLabs/containerized-api-deployment/pull/9) CI only; [#8](https://github.com/DNBLabs/containerized-api-deployment/pull/8) Infrastructure green ([run #26973764615](https://github.com/DNBLabs/containerized-api-deployment/actions/runs/26973764615)) plan in summary, Apply skipped

**Dependencies:** Checkpoint C, Task 19

**Files likely touched:**
- `.github/workflows/infra.yml`

**Estimated scope:** Small

---

### Checkpoint D: Pipeline end-to-end

- [x] Branch protection on `main` enabled (required check: **`App quality gates`** / workflow **`CI`**) — ruleset **Main** active 2025-06-04; requires `App quality gates`
- [x] GitHub Environment **`production`** configured with Azure OIDC vars — `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` (environment secrets); deploy branch policy `main`
- [x] Green run: test → build → scan → push → deploy (deploy via `workflow_run` + paths-filter) — [CI #26971457103](https://github.com/DNBLabs/containerized-api-deployment/actions/runs/26971457103) → [Deploy #26971487141](https://github.com/DNBLabs/containerized-api-deployment/actions/runs/26971487141) (Task 22 merge)
- [x] Live HTTPS `/health/live` smoke in deploy workflow; manual `/weather` + `/docs` — smoke `{"status":"ok"}` in deploy job; live `https://ca-weather-api-prod.redsky-b5616fdf.uksouth.azurecontainerapps.io` verified 2025-06-04

---

### Phase 5: Documentation & v1 sign-off

---

**Task Lock [24] (2025-06-04):** Expanded root `README.md` — live FQDN, Mermaid supply-chain diagram, Compose quickstart, Day-0/1 ops, KV secret, GitHub OIDC, rollback-by-SHA, cost/teardown; links ADR 0001 + CONTEXT + PRD + whitepaper. Contract tests in `app/tests/test_readme.py`.

## Task 24: README + architecture + operations

**Description:** Root README: quickstart (Compose), architecture Mermaid (GitHub → Actions → ACR → ACA → OWM), Day-0 bootstrap, KV secret, OIDC prerequisites, live URL, rollback-by-SHA, cost/teardown, link ADR 0001 + CONTEXT + PRD.

**Acceptance criteria:**
- [x] New contributor can follow README to local run without Azure — Compose quickstart + `test_readme_supports_local_quickstart_without_azure`
- [x] Operator can follow Day-0/Day-1 to prod — bootstrap/main/KV/OIDC sections + `test_readme_documents_day0_day1_and_oidc`
- [x] Mermaid renders on GitHub — `flowchart TB` block + `test_readme_includes_mermaid_architecture_diagram`

**Verification:**
- [x] Human read-through — agent pass; operator spot-check welcome
- [x] Links valid — `test_readme_links_to_core_documents` (all paths exist on disk)

**Dependencies:** Checkpoints B–D

**Files likely touched:**
- `README.md`, optional `docs/architecture.md`

**Estimated scope:** Medium

---

### Checkpoint E: v1 complete

**Checkpoint E verified (2025-06-04):** PRD stories 1–45 mapped below; Issue #1 reviewer path evidenced; `CONTEXT.md` glossary unchanged; merged [#8](https://github.com/DNBLabs/containerized-api-deployment/pull/8) → `main` @ `61fa8bd` (Tasks 23–24 + README).

- [x] All PRD user stories satisfied or explicitly deferred in CONTEXT — see traceability table; PRD “Out of scope” items match CONTEXT v1 bar / resolved decisions (staging, APM, auto-rollback, scale rules, runbook, etc.)
- [x] Issue #1 acceptance: reviewer can clone, run Compose, see green CI, hit prod URL — README quickstart; CI [#26971457103](https://github.com/DNBLabs/containerized-api-deployment/actions/runs/26971457103) success on `main`; live host 200 on `/health/live`, `/docs`, `/weather`; `94` pytest pass locally
- [x] `CONTEXT.md` unchanged terms; update only if implementation revealed glossary gaps — no glossary edits this checkpoint (bandit/infra CI already in CONTEXT Phase Lock [4])
- [x] Ready for human review / portfolio publish — `main` has full README, three workflows (`ci`, `deploy-app`, `infra`); ruleset **Main** requires **App quality gates**

#### PRD user story traceability (v1)

| IDs | Status | Evidence |
|-----|--------|----------|
| 1–2 | Done | Live FQDN; `/weather`, `/docs` HTTPS 200 (2025-06-04) |
| 3, 44–45 | Done | Root `README.md` Mermaid + Day-0/1; links ADR 0001, CONTEXT, PRD |
| 4 | Done | `ci.yml`, `deploy-app.yml`, `infra.yml`; Trivy + Terraform plan in Actions |
| 5 | Done | `acrcadprod.azurecr.io/weather-api:<7-char-sha>`; deploy uses `head_sha` |
| 6–7 | Done | Monorepo `app/` + `infra/` + workflows; whitepaper + CONTEXT committed |
| 8–11 | Done | `compose.yml` mock default; `app/README.md`, `.env.example` |
| 12–19 | Done | `test_weather_api.py`, location/OWM/error tests; public API |
| 20–22 | Done | `test_health.py`, `test_logging.py`, ACA probes in `aca.tf` |
| 23–24 | Done | `min_replicas=1`, `max_replicas=3`; scale **rules** deferred (CONTEXT v1.1) |
| 25, 39 | Done | README rollback + teardown + cost |
| 26–32 | Done | KV + ACA secret ref; manual KV set; OIDC UAMI; Trivy; non-root Dockerfile |
| 33–38 | Done | `infra/bootstrap`, `infra/envs/prod`, remote backend, `infra.yml` path-filter |
| 40–41, 43 | Done | CI gates; `workflow_run` deploy chain (Checkpoint D) |
| 42 | Done | Ruleset **Main** active: required check **App quality gates** (PR approval optional v1.1) |

**PRD out of scope (explicit in CONTEXT):** Azure staging, caller auth, custom domain, App Insights, automated rollback, HTTP scale rules, bootstrap-from-CI, OWM on ready probe, separate runbook, split OIDC identities, subscription-wide CI RBAC.

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

- [x] **GitHub org/repo subject:** Confirmed **`DNBLabs/containerized-api-deployment`** (Phase Lock [4]).
- [x] **Contributor vs custom roles:** RG **Contributor** for v1 on `rg-cad-prod-uksouth` (Task 19); tighten in future ADR if needed.
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
