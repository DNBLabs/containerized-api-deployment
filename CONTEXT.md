# Domain context — Containerized API Deployment

Glossary of terms agreed during design. Domain-facing language only; implementation lives in code and ADRs.

## Project

| Term | Definition |
|------|------------|
| **Reference implementation** | Primary goal: prove an end-to-end secure supply chain (container → registry → cloud → IaC → CI/CD). The application exists to exercise the pipeline, not as a standalone product roadmap. |
| **Production-grade delivery** | Secondary goal: operational and security practices are real enough to run in Azure with confidence (not a toy deploy), even though the app is a tracer bullet. |
| **Impressive** | Success is judged by a technical reviewer (e.g. hiring manager or senior engineer) who can validate depth without operating the system day-to-day. |
| **Azure subscription** | Personal subscription; production stack stays running for portfolio demos. README documents estimated monthly cost and teardown (`terraform destroy` / destroy order). |

## v1 production-grade bar

Capabilities required before v1 is "done":

| Capability | v1 |
|------------|-----|
| Live Azure deployment (public HTTPS) | Required |
| Two cloud environments (staging + prod) | Out of scope — local Docker + single Azure prod |
| OIDC GitHub Actions → Azure (no long-lived client secret in repo) | Required |
| Container hardening (non-root, minimal image, CI scan gate on Critical) | Required |
| Runtime secrets via Key Vault / platform secrets (not in image or plaintext state) | Required |
| Observability (structured logs, health/readiness) | Required |
| Full APM/tracing (App Insights, OpenTelemetry) | Out of scope for v1 |
| Terraform remote state (Azure Storage), separate state per environment | Required — prod state; local is not Terraform-managed |
| Automated rollback on failed deploy | Out of scope — manual revert to previous image tag, documented |

## Tracer application

| Term | Definition |
|------|------------|
| **Tracer API** | Small Python HTTP service used to exercise the supply chain; not a long-term product roadmap. |
| **Weather query** | `GET /weather` — return current weather for exactly one location input: either `city` **or** the pair `lat` + `lon` (mutually exclusive; validated at the API boundary). |
| **Weather response** | Normalized JSON summary (metric): `location`, `temperature_c`, `conditions`, `humidity_percent`, `wind_speed_mps`, `provider` (`mock` \| `openweathermap`), `observed_at`. Not a raw upstream pass-through. |
| **API errors** | HTTP 4xx/5xx use **RFC 7807** Problem Details (`application/problem+json`). |
| **Interactive API docs** | FastAPI Swagger UI at `/docs`, enabled in production for v1. |
| **Public API access** | The live ACA endpoint is anonymously callable; no caller API key or JWT in v1. Outbound OpenWeatherMap credential remains the only application secret. |
| **Continuous deployment** | Every merge to `main` that passes CI builds the image, pushes to ACR, and deploys a new ACA revision to production. |
| **Protected main branch** | `main` requires PR review and passing CI checks before merge (branch protection enabled in GitHub). |
| **Monorepo** | Single Git repository containing application code (`app/`), infrastructure (`infra/`), and GitHub Actions workflows (`.github/workflows/`). |
| **Repository root** | This workspace directory is the Git repository root pushed to GitHub. |
| **GitHub repository name** | `containerized-api-deployment` (new repository to be created). |
| **Azure region** | UK South (`uksouth`) — all prod resources in this region. |
| **Production resource group** | Single RG for v1: platform + runtime (ACR, ACA, Key Vault, Terraform state storage) co-located in `uksouth`. |
| **Terraform bootstrap** | Day-0 `infra/bootstrap/` applied once locally; uses **local state** (gitignored). Creates remote state storage for the main stack. |
| **Terraform main stack** | `infra/` (or `infra/envs/prod/`) uses **remote backend** (Azure Storage) created by bootstrap; not applied from CI until bootstrap exists. |
| **Container image tag** | Immutable **short Git SHA (7 characters)** per build (e.g. `weather-api:a1b2c3d`). No `latest` or floating tags in ACR for deployed revisions. |
| **Infrastructure CI** | Pull requests that touch `infra/**` must pass `terraform plan` (and other IaC checks). `terraform apply` to prod runs in CI only when `infra/**` changes on `main`. |
| **Application CI** | Every merge to `main` runs tests, builds image, pushes to ACR, and deploys ACA (new revision) without re-applying Terraform unless infra changed. |
| **ACA scale (prod)** | `minReplicas = 1`, `maxReplicas = 3`. HTTP/concurrency autoscaling rules deferred to v1.1 (no custom scale rules in v1 Terraform). |
| **Liveness probe** | `GET /health/live` — returns 200 if the process is running (no external dependencies). |
| **Readiness probe** | `GET /health/ready` — returns 200 when configured to serve traffic: required env/config present; when `WEATHER_PROVIDER=openweathermap`, `OPENWEATHERMAP_API_KEY` must be set. Does **not** call OpenWeatherMap on each check. |

## CI quality gates (v1)

All gates below must pass on pull requests to `main` before merge (branch protection). Deploy to prod runs only after they pass on `main`.

| Gate | v1 |
|------|-----|
| Unit tests (`pytest`) | Required |
| Lint/format (`ruff check`, `ruff format --check`) | Required |
| Type check (`mypy`) | Required |
| SAST (`bandit`) | Deferred (v1.1) |
| Container image scan (Trivy; fail on Critical) | Required |
| Terraform (`fmt`, `validate`; `plan` when PR touches `infra/**`) | Required (path-filtered plan) |

## Runtime stack

| Term | Definition |
|------|------------|
| **Python runtime** | CPython **3.12** (app, tests, CI, and container base image). |
| **Dependency management** | **`uv`** with `pyproject.toml` and committed lockfile; used in CI and Docker builds. |
| **Structured logging** | JSON lines to stdout (`timestamp`, `level`, `message`, `request_id`, `path`, `status_code`, `duration_ms`, `provider`, …). |
| **Request correlation** | **`X-Request-ID`**: honor client value if sent; otherwise generate UUID; echo on responses and include in logs and problem details where applicable. |
| **Local development** | **Docker Compose** is the primary path (`docker compose up`, `WEATHER_PROVIDER=mock` by default). **Native `uv run`** is optional for fast app iteration; both documented in README. |

## Documentation (v1)

| Artifact | v1 |
|----------|-----|
| `README.md` — quickstart, live URL, Day-0 bootstrap, Key Vault secret, rollback-by-SHA | Required |
| Architecture diagram (Mermaid in README or `docs/architecture.md`) | Required |
| `Containerized_API_Deployment_Whitepaper.md` in repo | Required |
| `CONTEXT.md` (domain glossary) | Committed |
| Separate `docs/runbook.md` | Deferred — operational steps live in README |

### Production resource names (v1, `uksouth`)

**Naming prefix:** `cad`

| Resource | Name |
|----------|------|
| Resource group | `rg-cad-prod-uksouth` |
| Container registry | `acrcadprod` (alphanumeric) |
| Key Vault | `kv-cad-prod-uks` |
| Container Apps environment | `cae-cad-prod-uksouth` |
| Container app | `ca-weather-api-prod` |
| ACR pull (ACA → ACR) | System-assigned managed identity on container app; **AcrPull** on `acrcadprod` |
| User-assigned managed identity (CI) | `id-cad-github-prod` — single identity for all GitHub Actions Azure operations (Terraform + ACR + ACA deploy). |
| GitHub OIDC federation | Federated credential subject limited to **`main`** branch: `repo:<owner>/containerized-api-deployment:ref:refs/heads/main`. No long-lived Azure client secrets in GitHub. |
| CI RBAC scope | Role assignments scoped to **`rg-cad-prod-uksouth`** only (not subscription-wide). |
| **Upstream weather provider** | OpenWeatherMap Current Weather API (live calls in prod when mock mode is off). |
| **Weather API credential** | Secret `OPENWEATHERMAP_API_KEY` — stored in Azure Key Vault in prod, injected into ACA as a platform secret; never baked into the image or committed to git. |
| **Key Vault secret provisioning** | The OpenWeatherMap key is set **manually once** after infrastructure exists (`az keyvault secret set` or equivalent); not stored in git or Terraform code. Documented in README. |
| **Azure Container App** | The single production runtime for the tracer container on Azure Container Apps (ACA). |
| **ACA ingress** | Public HTTPS via the platform-assigned default ACA FQDN (no custom domain in v1). |
| **Weather provider mode** | Configuration `WEATHER_PROVIDER`: `mock` (deterministic JSON, no outbound HTTP) or `openweathermap` (live upstream). Production ACA uses `openweathermap`; local Compose and CI default to `mock`. |

**Runtime modes (v1):** Hybrid — live upstream in Azure prod; mock mode available locally and in automated tests via environment flag.

## Resolved decisions

- **Purpose (2025-06-01):** Hybrid **Reference implementation + Production-grade delivery**. Portfolio/competency proof first; bar for security, automation, and operability matches what you would ship, not a slideshow demo.
- **v1 scope bar (2025-06-01):** Accepted minimum production-grade set above. Staging in Azure deferred; tracing deferred; rollback is manual via previous tag.
- **Tracer API behavior (2025-06-01):** Hybrid **C** — live upstream in prod; mock mode for local/CI via env flag.
- **Azure hosting (2025-06-01):** **ACA only** for v1; public HTTPS on default ACA FQDN (custom domain out of scope).
- **Upstream provider (2025-06-01):** **OpenWeatherMap** in prod; credential name `OPENWEATHERMAP_API_KEY` via Key Vault → ACA.
- **Application stack (2025-06-01):** **FastAPI**; single `GET /weather` endpoint; `/docs` exposed in prod for v1.
- **Caller authentication (2025-06-01):** **None** — fully public read-only API in v1.
- **Deployment trigger (2025-06-01):** **Auto deploy on `main`** after CI passes; **`main` branch-protected** (PR + green checks required).
- **Repository layout (2025-06-01):** **Monorepo** with `app/` + `infra/` + `.github/workflows/`.
- **GitHub home (2025-06-01):** Workspace root → new repo **`containerized-api-deployment`**.
- **Mock vs live toggle (2025-06-01):** **`WEATHER_PROVIDER`** — `mock` \| `openweathermap` (prod: `openweathermap`).
- **Azure region (2025-06-01):** **UK South (`uksouth`)**.
- **Terraform state bootstrap (2025-06-01):** **A+C** — local-state bootstrap once; main stack remote backend; documented manual Day-0.
- **Resource grouping (2025-06-01):** **Single production resource group** for all v1 Azure resources.
- **Image tagging (2025-06-01):** **Git short SHA only** — no `latest`; rollback by redeploying a prior SHA.
- **Terraform in CI (2025-06-01):** **Path-filtered apply** — plan on PRs affecting `infra/`; apply on `main` only when `infra/**` changes; app deploy every `main` merge.
- **ACA scaling (2025-06-01):** **`minReplicas = 1`** in production (always warm).
- **Health endpoints (2025-06-01):** **`/health/live`** + **`/health/ready`** (config check only; no upstream ping on ready).
- **CI quality gates (2025-06-01):** **pytest, ruff, mypy, Trivy (Critical), Terraform fmt/validate/plan** (path-filtered); bandit deferred.
- **Python version (2025-06-01):** **3.12**.
- **Azure naming (2025-06-01):** Prefix **`cad`** with prod/`uksouth` segments (see resource name table in glossary).
- **Key Vault secret bootstrap (2025-06-01):** **Manual one-shot** after infra apply; README-documented.
- **GitHub OIDC (2025-06-01):** **Single UAMI** `id-cad-github-prod`; federated trust **`main` only**; RBAC scoped to prod resource group.
- **ACA max scale (2025-06-01):** **`maxReplicas = 3`**; autoscaling rules deferred.
- **Weather API contract (2025-06-01):** **Normalized metric summary**; errors via **RFC 7807**.
- **Python dependencies (2025-06-01):** **`uv`** + lockfile.
- **Logging (2025-06-01):** **JSON lines** + **`X-Request-ID`** propagation.
- **Local development (2025-06-01):** **Compose primary** + optional **`uv run`**.
- **Documentation (2025-06-01):** **README + Mermaid diagram + whitepaper + CONTEXT.md**; runbook deferred.
- **ACR authentication (2025-06-01):** **System-assigned MI + AcrPull** (no admin user).
- **Azure subscription (2025-06-01):** **Personal sub**; prod left running; cost + teardown documented in README.
