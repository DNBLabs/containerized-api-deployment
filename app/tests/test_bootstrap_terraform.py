"""Terraform bootstrap stack tests (Task 14).

Public interface: `terraform init` + `terraform validate` in `infra/bootstrap/`.
Apply to Azure is operator-only (ADR 0001); not run in CI pytest.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_DIR = REPO_ROOT / "infra" / "bootstrap"

REQUIRED_OUTPUTS = (
    "resource_group_name",
    "storage_account_name",
    "container_name",
    "backend_config",
)

# Security contract for remote state storage (Task 14 hardening).
REQUIRED_STORAGE_HARDENING_PATTERNS = (
    r"storage_use_azuread\s*=\s*true",
    r"shared_access_key_enabled\s*=\s*false",
    r"infrastructure_encryption_enabled\s*=\s*true",
    r"https_traffic_only_enabled\s*=\s*true",
    r"allow_nested_items_to_be_public\s*=\s*false",
    r'container_access_type\s*=\s*"private"',
    r"use_azuread_auth\s*=\s*true",
)


def terraform_is_available() -> bool:
    """Return True when the Terraform CLI is on PATH."""
    return shutil.which("terraform") is not None


pytestmark = pytest.mark.skipif(
    not terraform_is_available(),
    reason="Terraform CLI not available",
)


def _run_terraform(*args: str, cwd: Path = BOOTSTRAP_DIR) -> subprocess.CompletedProcess[str]:
    """Run terraform in the bootstrap directory."""
    return subprocess.run(
        ["terraform", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="module")
def bootstrap_initialized() -> None:
    """Initialize bootstrap module without configuring a remote backend."""
    init = _run_terraform("init", "-backend=false")
    assert init.returncode == 0, init.stderr or init.stdout


def test_bootstrap_terraform_validates(bootstrap_initialized: None) -> None:
    """Bootstrap module passes terraform validate (static correctness)."""
    validate = _run_terraform("validate")
    assert validate.returncode == 0, validate.stderr or validate.stdout


def test_bootstrap_declares_backend_config_outputs() -> None:
    """Bootstrap exposes outputs an operator needs for the main stack backend."""
    outputs_tf = BOOTSTRAP_DIR / "outputs.tf"
    assert outputs_tf.is_file(), "infra/bootstrap/outputs.tf must exist"
    contents = outputs_tf.read_text(encoding="utf-8")
    for name in REQUIRED_OUTPUTS:
        assert re.search(rf'output\s+"{re.escape(name)}"\s+\{{', contents), (
            f'missing output "{name}" in outputs.tf'
        )


def test_bootstrap_storage_account_security_contract() -> None:
    """Bootstrap disables account keys and requires Entra-backed backend auth."""
    main_tf = BOOTSTRAP_DIR / "main.tf"
    outputs_tf = BOOTSTRAP_DIR / "outputs.tf"
    assert main_tf.is_file() and outputs_tf.is_file()
    combined = main_tf.read_text(encoding="utf-8") + outputs_tf.read_text(encoding="utf-8")
    for pattern in REQUIRED_STORAGE_HARDENING_PATTERNS:
        assert re.search(pattern, combined), f"missing bootstrap security setting: {pattern!r}"
