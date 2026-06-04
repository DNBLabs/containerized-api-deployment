"""GitHub Actions deploy-app workflow contract tests (Tasks 21–22 / Phase Lock [4]).

Public interface: `.github/workflows/deploy-app.yml` build, scan, push, and ACA deploy contract.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-app.yml"


def _deploy_workflow_text() -> str:
    """Return deploy-app.yml contents; fail fast if the workflow file is missing."""
    assert DEPLOY_WORKFLOW.is_file(), ".github/workflows/deploy-app.yml must exist"
    return DEPLOY_WORKFLOW.read_text(encoding="utf-8")


def test_deploy_app_workflow_triggers_after_ci_success_on_main() -> None:
    """Task 21: deploy runs via workflow_run after CI on main (Phase Lock [4])."""
    contents = _deploy_workflow_text()
    assert re.search(r"workflow_run\s*:", contents), "deploy-app.yml must use workflow_run trigger"
    assert re.search(
        r"workflows\s*:\s*(\[CI\]|\n\s*-\s*CI)",
        contents,
    ), "deploy-app.yml must listen for CI workflow completion"
    assert re.search(
        r"branches\s*:\s*(\[main\]|\n\s*-\s*main)",
        contents,
    ), "deploy-app.yml workflow_run must be limited to main"


def test_deploy_app_workflow_runs_only_after_successful_ci() -> None:
    """Phase Lock [4]: failed CI must not deploy."""
    contents = _deploy_workflow_text()
    assert "github.event.workflow_run.conclusion == 'success'" in contents


def test_deploy_app_workflow_runs_only_after_push_ci_on_same_repo() -> None:
    """Task Lock [21]: block PR/fork workflow_run from privileged deploy (pwn request class)."""
    contents = _deploy_workflow_text()
    assert "github.event.workflow_run.event == 'push'" in contents
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in contents


def test_deploy_app_workflow_scopes_oidc_to_build_job() -> None:
    """Task Lock [21]: gate job must not receive id-token write."""
    contents = _deploy_workflow_text()
    assert re.search(
        r"build-push-scan:[\s\S]*permissions:[\s\S]*id-token:\s*write",
        contents,
    )
    gate_section = contents.split("build-push-scan:")[0]
    assert "id-token: write" not in gate_section.split("gate:")[1]


def test_deploy_app_workflow_validates_image_tag_before_use() -> None:
    """Task Lock [21]: reject malformed tags before docker/trivy commands."""
    contents = _deploy_workflow_text()
    assert re.search(r"\^\[0-9a-f\]\{7\}\$", contents)


def test_deploy_app_workflow_hardens_checkout() -> None:
    """Task Lock [21]: minimal fetch and no persisted credentials on checkout."""
    contents = _deploy_workflow_text()
    assert contents.count("persist-credentials: false") >= 2
    assert contents.count("fetch-depth: 1") >= 2


def test_deploy_app_workflow_scans_before_push() -> None:
    """Task Lock [21]: Trivy must run before ACR push."""
    contents = _deploy_workflow_text()
    trivy_index = contents.index("Scan image for Critical vulnerabilities")
    push_index = contents.index("Push image to ACR")
    assert trivy_index < push_index


def test_deploy_app_workflow_checks_out_merged_commit() -> None:
    """Phase Lock [4]: image must match merged main SHA."""
    contents = _deploy_workflow_text()
    assert "github.event.workflow_run.head_sha" in contents


def test_deploy_app_workflow_tags_image_with_seven_char_sha() -> None:
    """Task 21: immutable short SHA tag for ACR."""
    contents = _deploy_workflow_text()
    assert re.search(
        r'HEAD_SHA:0:7|"acrcadprod\.azurecr\.io/weather-api:\$\{IMAGE_TAG\}"', contents
    )
    assert "acrcadprod.azurecr.io/weather-api" in contents
    assert not re.search(r"weather-api:latest", contents, re.IGNORECASE)


def test_deploy_app_workflow_fails_trivy_on_critical() -> None:
    """Task 21: Critical CVE blocks push."""
    contents = _deploy_workflow_text()
    assert re.search(r"aquasecurity/trivy-action@v\d+\.\d+\.\d+", contents), (
        "trivy-action must use a v-prefixed release tag (e.g. v0.36.0)"
    )
    assert re.search(r"severity:\s*CRITICAL", contents)
    assert re.search(r'exit-code:\s*"1"', contents)
    assert re.search(r'ignore-unfixed:\s*"true"', contents), (
        "ignore unfixed OS CVEs without published patches (e.g. debian perl-base)"
    )


def test_deploy_app_workflow_builds_from_app_context() -> None:
    """Phase Lock [2]: docker build context is app/."""
    contents = _deploy_workflow_text()
    assert re.search(r"docker build[\s\S]*\./app", contents)


def test_deploy_app_workflow_uses_production_environment_and_oidc() -> None:
    """Phase Lock [4]: Azure login via production environment secrets."""
    contents = _deploy_workflow_text()
    assert re.search(r"environment:\s*production", contents)
    assert "azure/login@v2" in contents
    assert "secrets.AZURE_CLIENT_ID" in contents
    assert "id-token: write" in contents


def test_deploy_app_workflow_updates_aca_revision_after_acr_push() -> None:
    """Task 22: roll ca-weather-api-prod to new image after ACR push (Phase Lock [4])."""
    contents = _deploy_workflow_text()
    push_index = contents.index("Push image to ACR")
    update_index = contents.index("Update ACA revision")
    assert push_index < update_index
    assert "az containerapp update" in contents
    assert "--name ca-weather-api-prod" in contents
    assert "--resource-group rg-cad-prod-uksouth" in contents
    assert "--container-name weather-api" in contents
    assert '--image "acrcadprod.azurecr.io/weather-api:${IMAGE_TAG}"' in contents


def test_deploy_app_workflow_smokes_health_live_after_aca_update() -> None:
    """Task Lock [22]: post-deploy smoke uses ingress FQDN and /health/live only."""
    contents = _deploy_workflow_text()
    update_index = contents.index("Update ACA revision")
    smoke_index = contents.index("Smoke test /health/live")
    assert update_index < smoke_index
    assert "az containerapp show" in contents
    assert "properties.configuration.ingress.fqdn" in contents
    assert 'curl -fsS "https://${FQDN}/health/live"' in contents
