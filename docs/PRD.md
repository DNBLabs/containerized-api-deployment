# PRD: Containerized API Deployment (v1)

**Status:** Ready for agent  
**Source:** `CONTEXT.md`, design session, ADR 0001, whitepaper  
**Tracker:** GitHub issue (label: `ready-for-agent`)

---

## Problem Statement

Engineering teams and individual practitioners need to demonstrate mastery of modern application delivery—immutable containers, infrastructure as code, and automated CI/CD—without the friction and risk of manual server configuration. The gap between “works on my machine” and a secure, repeatable production deployment creates bottlenecks, configuration drift, and weak supply-chain posture.

The user needs a **reference implementation** that proves an end-to-end **secure software supply chain** while meeting a **production-grade delivery** bar: a technical reviewer (e.g. hiring manager or senior engineer) can clone the repository, run the tracer API locally, inspect the pipeline, and hit a live HTTPS endpoint in Azure that behaves like a real service—not a slideshow demo.

Today the workspace contains only design artifacts (`CONTEXT.md`, whitepaper, ADR 0001). No application, infrastructure, or CI code exists yet.

---

## Solution

Deliver a **monorepo** (`containerized-api-deployment`) containing:

1. A **tracer API** — FastAPI weather service with hybrid **weather provider mode** (`mock` locally/CI, `openweathermap` in production).
2. **Containerization** — hardened Docker image (non-root, minimal base, scanned in CI).
3. **Azure production** — single region (`uksouth`), ACA hosting, private ACR, Key Vault for upstream credentials, public HTTPS on default ACA FQDN.
4. **Infrastructure as Code** — Terraform bootstrap (ADR 0001) plus main stack with remote state.
5. **CI/CD** — GitHub Actions with OIDC to Azure; auto-deploy app on every protected `main` merge; path-filtered Terraform apply when infrastructure changes.

Success is **impressive** when reviewers see: green pipeline, immutable SHA-tagged images, OIDC (no long-lived Azure secrets in the repo), structured logs, health probes, OpenAPI docs, normalized API contract, and documented Day-0/Day-2 operations (bootstrap, secret placement, rollback by SHA, teardown/cost).

---

## User Stories

### Reviewer & portfolio

1. As a **technical reviewer**, I want a public HTTPS URL to call `GET /weather`, so that I can verify the live deployment without cloning the repo.
2. As a **technical reviewer**, I want interactive OpenAPI docs at `/docs` on production, so that I can explore the API contract quickly.
3. As a **technical reviewer**, I want a README with architecture diagram and Day-0 steps, so that I can understand the system in under ten minutes.
4. As a **technical reviewer**, I want evidence of CI quality gates (tests, lint, typecheck, image scan, Terraform plan), so that I can trust the supply chain discipline.
5. As a **technical reviewer**, I want immutable image tags tied to Git SHAs, so that I can trace running software to source control.
6. As a **hiring manager**, I want the repository to demonstrate cross-functional competence (app + cloud + IaC + CI), so that I can assess modern delivery skills.
7. As a **candidate/author**, I want the whitepaper and `CONTEXT.md` in the repo, so that narrative and implementation stay aligned.

### Local development

8. As a **developer**, I want `docker compose up` to run the API with `WEATHER_PROVIDER=mock` by default, so that I do not need Azure or OpenWeatherMap keys locally.
9. As a **developer**, I want optional native `uv run` for fast iteration, so that I can change application code without rebuilding containers constantly.
10. As a **developer**, I want deterministic mock weather responses, so that local behavior is stable for manual testing and demos.
11. As a **developer**, I want clear environment variable documentation, so that I know how to switch between mock and live upstream modes.

### Weather API consumers

12. As an **API consumer**, I want `GET /weather?city=...` to return current weather, so that I can query by city name.
13. As an **API consumer**, I want `GET /weather?lat=...&lon=...` to return current weather, so that I can query by coordinates.
14. As an **API consumer**, I want validation errors when I supply both city and coordinates or neither, so that the contract is unambiguous.
15. As an **API consumer**, I want responses in a normalized metric JSON shape (`temperature_c`, `wind_speed_mps`, etc.), so that I am not exposed to raw upstream payloads.
16. As an **API consumer**, I want a `provider` field in responses (`mock` or `openweathermap`), so that I know which backend served the data.
17. As an **API consumer**, I want RFC 7807 error bodies for 4xx/5xx, so that failures are machine-readable and consistent.
18. As an **API consumer**, I want `X-Request-ID` on responses, so that I can correlate client issues with server logs.
19. As an **API consumer**, I want the API to be anonymously callable in v1, so that I can try it without obtaining credentials (understanding abuse risk is on the operator).

### Operations & health

20. As a **platform operator**, I want `GET /health/live` for liveness, so that ACA can restart unhealthy instances.
21. As a **platform operator**, I want `GET /health/ready` that validates configuration without calling OpenWeatherMap, so that routing reflects readiness without upstream flapping.
22. As a **platform operator**, I want structured JSON logs with `request_id`, so that I can diagnose requests in Azure log aggregation.
23. As a **platform operator**, I want production to keep at least one replica warm (`minReplicas=1`), so that demo URLs respond without cold start.
24. As a **platform operator**, I want `maxReplicas=3`, so that the platform can scale modestly under load (rules deferred).
25. As a **platform operator**, I want documented manual rollback via redeploying a prior image SHA, so that I can recover from a bad release without automated rollback machinery.

### Secrets & security

26. As a **security-conscious operator**, I want the OpenWeatherMap key in Key Vault and injected into ACA, so that secrets are not in git, images, or plaintext Terraform state.
27. As a **security-conscious operator**, I want to set the Key Vault secret manually once after infra exists, so that the key never transits through CI logs.
28. As a **security-conscious operator**, I want GitHub Actions to authenticate via OIDC with a single user-assigned identity scoped to the production resource group, so that there are no long-lived Azure client secrets in GitHub.
29. As a **security-conscious operator**, I want federated credentials limited to the `main` branch, so that feature branches cannot deploy to production.
30. As a **security-conscious operator**, I want ACA to pull from ACR via system-assigned managed identity with AcrPull, so that ACR admin users are not used.
31. As a **security-conscious operator**, I want container images scanned in CI with failure on Critical vulnerabilities, so that known-critical images do not deploy.
32. As a **security-conscious operator**, I want the container to run as a non-root user on a minimal base image, so that runtime attack surface is reduced.

### Infrastructure & Terraform

33. As an **operator**, I want a bootstrap Terraform stack with local state to create remote state storage, so that the main stack can use Azure Storage backend per ADR 0001.
34. As an **operator**, I want the main Terraform stack to provision RG, ACR, Key Vault, ACA environment, and container app in `uksouth`, so that production is fully declarative.
35. As an **operator**, I want consistent `cad` naming for Azure resources, so that resources are identifiable in the portal.
36. As an **operator**, I want `terraform plan` on PRs that touch infrastructure, so that infra changes are reviewed before merge.
37. As an **operator**, I want `terraform apply` in CI only when `infra/**` changes on `main`, so that app deploys do not unnecessarily re-apply infrastructure.
38. As an **operator**, I want remote Terraform state for the main stack, so that state is durable and lockable.
39. As an **operator**, I want README teardown instructions and cost guidance, so that I can destroy resources when I stop paying for the demo.

### CI/CD

40. As a **developer**, I want every merge to protected `main` to run pytest, ruff, and mypy before deploy, so that quality regressions do not reach production.
41. As a **developer**, I want each `main` merge to build, tag with short Git SHA, push to ACR, and deploy ACA, so that delivery is continuous.
42. As a **developer**, I want branch protection requiring PR and green checks, so that direct pushes to `main` cannot bypass gates.
43. As a **developer**, I want CI to use `WEATHER_PROVIDER=mock`, so that pipelines do not depend on external APIs or secrets.

### Documentation

44. As a **developer**, I want a Mermaid architecture diagram, so that components and data flow are visible at a glance.
45. As a **developer**, I want ADR 0001 referenced from README, so that bootstrap trade-offs are understandable.

---

## Implementation Decisions

### Architectural shape

- **Monorepo** with `app/` (tracer API), `infra/` (Terraform), `infra/bootstrap/` (Day-0 per ADR 0001), `.github/workflows/` (CI/CD).
- **Phased delivery** aligned to whitepaper: (1) API, (2) containerization, (3) IaC, (4) pipeline—orchestration can be incremental but v1 is not complete until all four are integrated.
- **Single Azure production environment** in `uksouth`; local parity via Docker Compose only (no Azure staging).
- **Repository name:** `containerized-api-deployment` under GitHub owner `DNBLabs` (or equivalent when created).

### Deep modules (build or modify)

These modules encapsulate volatile or complex logic behind stable, testable interfaces:

| Module | Responsibility | Interface (conceptual) |
|--------|----------------|-------------------------|
| **Weather provider** | Fetch/normalize weather from mock or OpenWeatherMap | `get_current_weather(location: Location) -> WeatherSummary` keyed by `WEATHER_PROVIDER` |
| **Location validation** | Enforce city XOR (lat + lon) | `parse_location_query(...) -> Location` raises domain validation errors |
| **Upstream HTTP client** | Timeouts, error mapping for OpenWeatherMap | Thin wrapper used only by OpenWeatherMap provider |
| **Health readiness** | Config checks for live vs mock mode | `check_ready() -> ReadyStatus` |
| **Request correlation** | `X-Request-ID` propagate/generate | Middleware: attach `request_id` to request state and response headers |
| **Structured logging** | JSON log lines with standard fields | Logger adapter/context binding per request |
| **Problem details mapping** | RFC 7807 for HTTP exceptions | Exception handlers: validation, upstream timeout, upstream error, internal |
| **Terraform bootstrap** | Remote state storage (ADR 0001) | Independent root module; local state only |
| **Terraform main stack** | Prod RG, ACR, KV, ACA env, container app, RBAC for CI and runtime identities | Root or `envs/prod` with azurerm remote backend |
| **CI app workflow** | Test, build, scan, push, deploy revision | Inputs: SHA; OIDC login; no Terraform unless shared job |
| **CI infra workflow** | fmt, validate, plan/apply path-filtered | Triggers on `infra/**` changes |

Shallow layers (thin wiring): FastAPI route handlers call weather provider; Terraform wires resources; workflows orchestrate CLI tools.

### Tracer API contract

- **Endpoint:** `GET /weather` with query params: `city` OR (`lat` AND `lon`).
- **Success body (metric, normalized):** `location`, `temperature_c`, `conditions`, `humidity_percent`, `wind_speed_mps`, `provider`, `observed_at`.
- **Errors:** `application/problem+json` (RFC 7807); include `request_id` extension when available.
- **Docs:** `/docs` enabled in production (v1).
- **Health:** `/health/live` (process up); `/health/ready` (config present; if `openweathermap`, `OPENWEATHERMAP_API_KEY` set—no upstream ping).

### Configuration

- `WEATHER_PROVIDER`: `mock` | `openweathermap` (prod ACA: `openweathermap`; Compose/CI default: `mock`).
- `OPENWEATHERMAP_API_KEY`: required when provider is `openweathermap`; sourced from Key Vault → ACA secret reference in prod.

### Container

- Python **3.12**, dependencies via **`uv`** + lockfile.
- Multi-stage or slim build; **non-root** user; expose application port only.
- Image name/tag: `weather-api:<7-char-sha>` in ACR `acrcadprod`; no `latest` for deployed revisions.

### Azure resources (production)

- RG: `rg-cad-prod-uksouth`
- ACR: `acrcadprod` (AcrPull via ACA system-assigned MI)
- Key Vault: `kv-cad-prod-uks`
- ACA environment: `cae-cad-prod-uksouth`
- Container app: `ca-weather-api-prod` — `minReplicas=1`, `maxReplicas=3`, public ingress on default FQDN
- CI identity: `id-cad-github-prod` — OIDC federated to `repo:<owner>/containerized-api-deployment:ref:refs/heads/main`; RBAC scoped to prod RG

### Terraform (ADR 0001)

- Bootstrap: manual once, local gitignored state, creates backend storage.
- Main stack: remote backend; CI `apply` only on `infra/**` changes to `main`.
- OpenWeatherMap secret **not** in Terraform code; manual `az keyvault secret set` documented post-apply.

### CI/CD

- Gates on PR to `main`: pytest, ruff (check + format), mypy, Trivy (fail Critical), Terraform fmt/validate/plan when `infra/**` touched.
- On `main` merge: always app pipeline (test → build → scan → push → ACA deploy); conditionally infra apply.
- Authentication: Azure OIDC only (no `AZURE_CREDENTIALS` client secret in repo).

### Type shape (weather summary — from design)

```json
{
  "location": "London, GB",
  "temperature_c": 14.2,
  "conditions": "light rain",
  "humidity_percent": 72,
  "wind_speed_mps": 4.1,
  "provider": "openweathermap",
  "observed_at": "2025-06-01T12:00:00Z"
}
```

---

## Testing Decisions

### Principles

- Test **external behavior** at module boundaries: HTTP status, JSON body shape, problem detail `type`/`title`, health codes, provider selection via env.
- **Do not** assert internal call order unless testing resilience contracts (e.g. timeout → 502 problem).
- Use **httpx mocking** (or equivalent) for OpenWeatherMap provider tests—no live network in unit/CI tests.
- Terraform: rely on **`terraform validate`** and **`plan`** in CI; optional future `terraform test` hooks—not traditional unit tests for HCL in v1.

### Modules to test (recommended)

| Module | Test focus |
|--------|------------|
| **Location validation** | city-only, lat/lon-only, both, neither → validation problem |
| **Mock weather provider** | deterministic output; `provider=mock` |
| **OpenWeatherMap provider** | maps fixture upstream JSON → normalized summary; timeout/error → problem |
| **Health readiness** | missing API key when `openweathermap` → not ready; mock mode ready without key |
| **HTTP API (integration)** | `TestClient`: `/weather`, `/health/*`, `/docs` availability, `X-Request-ID` echo/generate |
| **Request correlation** | optional: middleware unit tests for header pass-through |

### Modules with lighter or no direct unit tests in v1

- **Terraform modules:** validated via fmt/validate/plan in CI.
- **GitHub workflows:** verified by running pipeline on PR (manual/E2E).
- **Dockerfile:** covered indirectly by Trivy + container smoke in CI if added.

### Prior art

- Greenfield repository—no existing test patterns. Establish pytest + pytest-asyncio (if async routes) conventions under `app/tests/`.

---

## Out of Scope

- Azure **staging** environment (second cloud env); local Docker only for non-prod.
- **Caller authentication** (API keys, JWT) on the tracer API.
- **Custom domain** and TLS certificate management beyond ACA default FQDN.
- **App Insights / OpenTelemetry** tracing (structured logs only in v1).
- **Automated rollback** on failed deploy (manual SHA redeploy documented only).
- **HTTP/concurrency autoscaling rules** for ACA (min/max replica bounds only).
- **bandit** SAST (deferred v1.1).
- **ACR `latest` tag** or floating deploy tags.
- **Bootstrap Terraform from CI** (per ADR 0001).
- **OpenWeatherMap on readiness probes**.
- Separate **`docs/runbook.md`** (content lives in README).
- **Split GitHub OIDC identities** for infra vs deploy (single UAMI in v1).
- **Subscription-wide RBAC** for CI (RG-scoped only).

---

## Further Notes

- **Cost:** Document ~£15–40/month ballpark for always-on `minReplicas=1` in UK South; include teardown order (main stack destroy before bootstrap considerations per ADR 0001).
- **OpenWeatherMap:** Operator must obtain API key; free tier subject to upstream rate limits—implement sensible HTTP timeouts and 502/503 problem mapping.
- **GitHub repo:** Create `DNBLabs/containerized-api-deployment`, enable branch protection on `main`, create `ready-for-agent` label for agent pickup.
- **Future ADR candidate:** Tightening CI RBAC below RG Contributor to role bundles (AcrPush + Container Apps Contributor + Storage for state)—not required for v1.
- **Agent implementation order suggestion:** Phase 1 app + tests → Phase 2 Dockerfile + Compose → Phase 3 bootstrap + main Terraform → Phase 4 workflows + OIDC wiring → README/diagram polish.
