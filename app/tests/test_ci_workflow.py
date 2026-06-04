"""GitHub Actions CI workflow contract tests (Task 20 / Phase Lock [4]).

Public interface: `.github/workflows/ci.yml` triggers and quality gates match CONTEXT.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _ci_workflow_text() -> str:
    """Return ci.yml contents; fail fast if the workflow file is missing."""
    assert CI_WORKFLOW.is_file(), ".github/workflows/ci.yml must exist"
    return CI_WORKFLOW.read_text(encoding="utf-8")


def test_ci_workflow_triggers_on_pull_request_to_main() -> None:
    """Task 20: app quality gates run on PRs targeting main (Phase Lock [4])."""
    contents = _ci_workflow_text()
    assert re.search(
        r"pull_request\s*:\s*\n\s*branches\s*:\s*\[\s*main\s*\]",
        contents,
    ), "ci.yml must declare pull_request trigger for branch main"


def test_ci_workflow_triggers_on_push_to_main() -> None:
    """Task 20: app quality gates re-run on merge to main."""
    contents = _ci_workflow_text()
    assert re.search(
        r"push\s*:\s*\n\s*branches\s*:\s*\[\s*main\s*\]",
        contents,
    ), "ci.yml must declare push trigger for branch main"


def test_ci_workflow_job_name_matches_branch_protection() -> None:
    """Phase Lock [4]: required check name App quality gates."""
    contents = _ci_workflow_text()
    assert re.search(
        r'name:\s*App quality gates',
        contents,
    ), "ci.yml job must be named App quality gates for branch protection"


def test_ci_workflow_runs_bandit_on_weather_api_source() -> None:
    """Task 20 / CONTEXT: bandit required on src/weather_api."""
    contents = _ci_workflow_text()
    assert "uv run bandit -r src/weather_api" in contents
