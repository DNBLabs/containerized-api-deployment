# ADR 0001: Terraform remote state bootstrap with local Day-0 state

**Status:** Accepted  
**Date:** 2025-06-01  
**Deciders:** Project owner (design session)

## Context

The v1 architecture provisions Azure resources with Terraform and requires **remote state** in Azure Storage (team-safe locking, no state in git). Remote state storage cannot be created by the same Terraform stack that consumes it without a bootstrap step—the backend block must point at an existing storage account and container.

Alternatives considered:

1. **Bootstrap stack with local state** — `infra/bootstrap/` applied once from an operator workstation; state file gitignored.
2. **Bootstrap via CI** — GitHub Actions creates the state backend on first run.
3. **Bootstrap with remote state from the start** — Requires a second “meta” backend or manual `az` creation only for state (equivalent to partial manual Day-0).

Constraints from project context:

- Single production environment in `uksouth`; monorepo with path-filtered `terraform apply` on `infra/**` changes.
- GitHub OIDC to Azure (no long-lived client secrets in the repository).
- Portfolio/reference implementation: Day-0 steps must be documentable and reproducible without over-automating the chicken-and-egg problem.

## Decision

We will use a **dedicated bootstrap Terraform root module** at `infra/bootstrap/` that:

1. Creates the Azure Storage account and container used for Terraform remote state (and related bootstrap resources as needed).
2. Uses **local Terraform state** for the bootstrap module only, with `*.tfstate` and backup files **gitignored**.
3. Is applied **once manually** by the operator after authenticating to Azure (`az login` or equivalent), following README Day-0 instructions.
4. Is followed by configuring the **main** stack (`infra/` or `infra/envs/prod/`) to use an `azurerm` remote backend targeting resources created by bootstrap.

The main stack’s remote state is the source of truth for all production infrastructure after bootstrap. CI may run `terraform apply` on the main stack when `infra/**` changes on `main`, but **bootstrap is not executed from CI** in v1.

## Consequences

### Positive

- Avoids storing Terraform state in git or passing state through CI artifacts.
- Clear separation between **Day-0** (bootstrap, local state) and **Day-1+** (main stack, remote state, CI-capable).
- No circular dependency: main backend configuration references resources that already exist.
- Aligns with least exposure of bootstrap credentials in GitHub (bootstrap runs under operator identity, not pipeline).

### Negative

- Bootstrap state lives on the operator machine unless they manually back it up; **loss of local bootstrap state** can make it awkward to destroy or update bootstrap resources without import/drift work.
- Bootstrap is not fully automated; new environments (e.g. staging in Azure) require repeating or extending bootstrap.
- Drift between bootstrap and main stack is possible if someone changes state storage outside Terraform.

### Mitigations

- README documents bootstrap apply, backend configuration, and a **teardown order** (destroy main stack before bootstrap, or document orphan risks).
- Gitignore rules for `infra/bootstrap/terraform.tfstate*`.
- Optional: store bootstrap state copy in a secure personal vault (out of repo) if the operator wants insurance.

## Related

- `CONTEXT.md` — Terraform bootstrap, production resource group, CI path-filtered apply.
- Future ADRs may cover tightening GitHub OIDC RBAC below resource-group Contributor if scope is reduced further.
