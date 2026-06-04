"""GitHub Actions infra workflow contract tests (Task 23 / Phase Lock [4]).

Public interface: `.github/workflows/infra.yml` path-filtered Terraform CI contract.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "infra.yml"


def _infra_workflow_text() -> str:
    """Return infra.yml contents; fail fast if the workflow file is missing."""
    assert INFRA_WORKFLOW.is_file(), ".github/workflows/infra.yml must exist"
    return INFRA_WORKFLOW.read_text(encoding="utf-8")


def test_infra_workflow_triggers_only_when_infra_changes() -> None:
    """Task 23: app-only PRs must not run infra workflow (paths filter infra/**)."""
    contents = _infra_workflow_text()
    assert re.search(
        r"pull_request\s*:[\s\S]*?paths\s*:[\s\S]*?-\s*['\"]infra/\*\*['\"]",
        contents,
    ), "infra.yml pull_request must path-filter infra/**"
    assert re.search(
        r"push\s*:[\s\S]*?paths\s*:[\s\S]*?-\s*['\"]infra/\*\*['\"]",
        contents,
    ), "infra.yml push must path-filter infra/**"


def test_infra_workflow_does_not_apply_on_pull_request() -> None:
    """Task 23: PRs with infra changes plan only; no terraform apply."""
    contents = _infra_workflow_text()
    assert re.search(
        r"name:\s*Terraform Apply[\s\S]*?if:\s*github\.event_name == 'push'",
        contents,
    ), "terraform apply must be gated to push events only"
    assert "terraform apply" not in contents.split("Terraform Apply")[0]


def test_infra_workflow_publishes_plan_to_job_summary() -> None:
    """Task 23: infra PRs expose plan output in the Actions job summary."""
    contents = _infra_workflow_text()
    assert "GITHUB_STEP_SUMMARY" in contents
    assert "terraform show -no-color tfplan" in contents


def test_infra_workflow_runs_fmt_validate_and_plan() -> None:
    """CONTEXT: infra CI runs fmt -check, validate, and plan before apply."""
    contents = _infra_workflow_text()
    assert "terraform fmt -check" in contents
    assert "terraform validate" in contents
    plan_index = contents.index("terraform plan")
    apply_index = contents.index("Terraform Apply")
    assert plan_index < apply_index


def test_infra_workflow_uses_terraform_oidc_not_azure_cli() -> None:
    """azurerm on GHA must use OIDC env vars, not Azure CLI service principal auth."""
    contents = _infra_workflow_text()
    assert re.search(r'ARM_USE_OIDC:\s*"?true"?', contents)
    assert "ARM_CLIENT_ID" in contents
    assert "secrets.AZURE_CLIENT_ID" in contents


def test_infra_workflow_uses_prod_stack_and_entra_backend_auth() -> None:
    """Phase Lock [4]: prod working dir and ARM_USE_AZUREAD for remote state."""
    contents = _infra_workflow_text()
    assert re.search(
        r"working-directory:\s*infra/envs/prod",
        contents,
    )
    assert re.search(r'ARM_USE_AZUREAD:\s*"?true"?', contents)
    assert "terraform init -backend-config=backend.hcl" in contents
    assert "cp backend.hcl.example backend.hcl" in contents


def test_infra_workflow_uses_production_environment_and_oidc() -> None:
    """Phase Lock [4]: Azure OIDC via production environment secrets."""
    contents = _infra_workflow_text()
    assert re.search(r"environment:\s*production", contents)
    assert "azure/login@v2" in contents
    assert "secrets.AZURE_CLIENT_ID" in contents
    assert "id-token: write" in contents


def test_infra_workflow_queues_infra_runs_without_cancel() -> None:
    """Phase Lock [4]: infra-prod concurrency does not cancel in-progress applies."""
    contents = _infra_workflow_text()
    assert re.search(r"group:\s*infra-prod", contents)
    assert re.search(r"cancel-in-progress:\s*false", contents)
