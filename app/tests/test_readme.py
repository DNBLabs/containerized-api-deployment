"""Root README contract tests (Task 24).

Public interface: README.md contains operator/contributor sections and valid doc links.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"

DOC_LINKS = (
    "CONTEXT.md",
    "docs/PRD.md",
    "docs/adr/0001-terraform-remote-state-bootstrap.md",
    "docs/Containerized_API_Deployment_Whitepaper.md",
    "IMPLEMENTATION_PLAN.md",
    "infra/bootstrap/README.md",
    "infra/envs/prod/README.md",
    "app/README.md",
    ".env.example",
)


def _readme_text() -> str:
    """Return README.md contents; fail fast if missing."""
    assert README.is_file(), "README.md must exist at repository root"
    return README.read_text(encoding="utf-8")


def test_readme_supports_local_quickstart_without_azure() -> None:
    """Task 24: contributor path uses Compose and mock weather only."""
    contents = _readme_text()
    assert "docker compose up" in contents
    assert "Quickstart (local, no Azure)" in contents
    assert "mock" in contents.lower()
    assert "OPENWEATHERMAP_API_KEY" not in contents.split("Quickstart")[1].split("Production")[0]


def test_readme_documents_day0_day1_and_oidc() -> None:
    """Task 24: operator can bootstrap, apply prod, set KV secret, configure GitHub OIDC."""
    contents = _readme_text()
    assert "Day-0" in contents
    assert "Day-1" in contents
    assert "infra/bootstrap" in contents
    assert "infra/envs/prod" in contents
    assert "keyvault secret set" in contents.lower()
    assert "AZURE_CLIENT_ID" in contents
    assert "production" in contents


def test_readme_includes_mermaid_architecture_diagram() -> None:
    """Task 24: architecture Mermaid block renders on GitHub."""
    contents = _readme_text()
    assert re.search(r"```mermaid\s*\nflowchart", contents)
    assert "GitHub Actions" in contents or "gh[" in contents


def test_readme_links_to_core_documents() -> None:
    """Task 24: links to ADR 0001, CONTEXT, PRD, and nested operator READMEs."""
    contents = _readme_text()
    for rel_path in DOC_LINKS:
        assert rel_path in contents, f"README must reference {rel_path}"
        assert (REPO_ROOT / rel_path).is_file(), f"missing linked file: {rel_path}"


def test_readme_covers_rollback_cost_and_teardown() -> None:
    """Task 24: rollback-by-SHA, cost ballpark, and destroy order documented."""
    contents = _readme_text()
    assert "Rollback" in contents
    assert "7-char" in contents or "7-char-git-sha" in contents
    assert "terraform destroy" in contents
    assert "£" in contents or "month" in contents.lower()
