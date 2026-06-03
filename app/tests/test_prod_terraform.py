"""Terraform production main stack tests (Task 15).

Public interface: terraform init (backend config file) and terraform validate in infra/envs/prod/.
Remote backend apply requires bootstrap outputs and Azure auth (operator/CI).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROD_DIR = REPO_ROOT / "infra" / "envs" / "prod"

REQUIRED_VARIABLES = ("location", "prefix", "tags")

REQUIRED_BACKEND_HCL_KEYS = (
    "resource_group_name",
    "storage_account_name",
    "container_name",
    "key",
    "use_azuread_auth",
)

PROD_SECURITY_PATTERNS = (
    r"storage_use_azuread\s*=\s*true",
    r'backend\s+"azurerm"\s+\{\s*\}',
    r"use_azuread_auth\s*=\s*true",
)

FORBIDDEN_BACKEND_SECRET_KEYS = (
    "access_key",
    "storage_account_key",
    "sas_token",
)


def terraform_is_available() -> bool:
    """Return True when the Terraform CLI is on PATH."""
    return shutil.which("terraform") is not None


pytestmark = pytest.mark.skipif(
    not terraform_is_available(),
    reason="Terraform CLI not available",
)


def _run_terraform(*args: str, cwd: Path = PROD_DIR) -> subprocess.CompletedProcess[str]:
    """Run terraform in the production stack directory."""
    return subprocess.run(
        ["terraform", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="module")
def prod_initialized() -> None:
    """Initialize prod module without configuring the remote backend (CI-safe)."""
    assert PROD_DIR.is_dir(), "infra/envs/prod must exist"
    init = _run_terraform("init", "-backend=false")
    assert init.returncode == 0, init.stderr or init.stdout


def test_prod_stack_terraform_validates(prod_initialized: None) -> None:
    """Production stack passes terraform validate (static correctness)."""
    validate = _run_terraform("validate")
    assert validate.returncode == 0, validate.stderr or validate.stdout


def test_prod_stack_declares_core_variables() -> None:
    """Production stack exposes CONTEXT-aligned input variables."""
    variables_tf = PROD_DIR / "variables.tf"
    assert variables_tf.is_file()
    contents = variables_tf.read_text(encoding="utf-8")
    for name in REQUIRED_VARIABLES:
        assert re.search(rf'variable\s+"{re.escape(name)}"\s+\{{', contents), (
            f'missing variable "{name}" in variables.tf'
        )
    assert 'default     = "cad"' in contents
    assert 'default     = "uksouth"' in contents


def test_prod_stack_backend_config_template_uses_entra_id() -> None:
    """Backend config template matches bootstrap contract (Entra ID, no keys)."""
    backend_example = PROD_DIR / "backend.hcl.example"
    assert backend_example.is_file()
    contents = backend_example.read_text(encoding="utf-8")
    for key in REQUIRED_BACKEND_HCL_KEYS:
        assert key in contents, f"missing {key!r} in backend.hcl.example"
    assert "use_azuread_auth     = true" in contents


def test_prod_stack_plans_prod_resource_group_name() -> None:
    """Skeleton locals match CONTEXT production resource group naming."""
    main_tf = PROD_DIR / "main.tf"
    assert main_tf.is_file()
    contents = main_tf.read_text(encoding="utf-8")
    assert "rg-${var.prefix}-${var.environment}-${var.location}" in contents


def test_prod_stack_remote_state_security_contract() -> None:
    """Main stack uses Entra ID for backend and provider; backend template has no keys."""
    versions_tf = PROD_DIR / "versions.tf"
    backend_example = PROD_DIR / "backend.hcl.example"
    outputs_tf = PROD_DIR / "outputs.tf"
    assert versions_tf.is_file() and backend_example.is_file() and outputs_tf.is_file()
    combined = (
        versions_tf.read_text(encoding="utf-8")
        + backend_example.read_text(encoding="utf-8")
        + outputs_tf.read_text(encoding="utf-8")
    )
    for pattern in PROD_SECURITY_PATTERNS:
        assert re.search(pattern, combined), f"missing prod security setting: {pattern!r}"
    backend_contents = backend_example.read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_BACKEND_SECRET_KEYS:
        assert not re.search(rf"^\s*{forbidden}\s*=", backend_contents, re.MULTILINE), (
            f"backend.hcl.example must not set {forbidden!r}"
        )
    assert re.search(r'output\s+"security_notes"\s+\{', outputs_tf.read_text(encoding="utf-8"))
