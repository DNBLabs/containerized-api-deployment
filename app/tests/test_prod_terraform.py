"""Terraform production main stack tests (Tasks 15–19).

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

CONTEXT_PROD_RG_NAME = "rg-cad-prod-uksouth"
CONTEXT_ACR_NAME = "acrcadprod"
CONTEXT_KEY_VAULT_NAME = "kv-cad-prod-uks"
CONTEXT_CAE_NAME = "cae-cad-prod-uksouth"
CONTEXT_CONTAINER_APP_NAME = "ca-weather-api-prod"
CONTEXT_GITHUB_CI_IDENTITY_NAME = "id-cad-github-prod"
CONTEXT_GITHUB_ORG = "DNBLabs"
CONTEXT_GITHUB_REPO = "containerized-api-deployment"

TASK19_GITHUB_IDENTITY_PATTERNS = (
    r'resource\s+"azurerm_user_assigned_identity"\s+"github_ci"',
    rf'name\s*=\s*"{re.escape(CONTEXT_GITHUB_CI_IDENTITY_NAME)}"',
)

TASK19_FEDERATED_CREDENTIAL_PATTERNS = (
    r'resource\s+"azurerm_federated_identity_credential"\s+"github_main"',
    r'issuer\s*=\s*"https://token\.actions\.githubusercontent\.com"',
    r'audience\s*=\s*\["api://AzureADTokenExchange"\]',
    r"subject\s*=\s*local\.github_federated_subject",
)

TASK19_FORBIDDEN_OIDC_PATTERNS = (
    r"azurerm_client_secret",
    r"client_secret\s*=",
    r"password\s*=",
    r"subject\s*=.*pull_request",
    r"subject\s*=.*environment:",
    r"ref:refs/heads/\*",
    r'resource\s+"azurerm_federated_identity_credential"[^}]*subject\s*=\s*"[^"]*\*',
)

TASK19_CI_RBAC_PATTERNS = (
    r'resource\s+"azurerm_role_assignment"\s+"github_ci_rg_contributor"',
    r'role_definition_name\s*=\s*"Contributor"',
    r"azurerm_resource_group\.prod\.id",
    r"azurerm_user_assigned_identity\.github_ci\.principal_id",
)

FORBIDDEN_GITHUB_OIDC_OUTPUTS = (
    "client_secret",
    "azurerm_client_secret",
    "password",
)

ACA_RESOURCE_PATTERNS = (
    r'resource\s+"azurerm_container_app_environment"\s+"prod"',
    r'resource\s+"azurerm_container_app"\s+"weather_api"',
)

ACA_INGRESS_AND_SCALE_PATTERNS = (
    r"external_enabled\s*=\s*true",
    r"target_port\s*=\s*8000",
    r"min_replicas\s*=\s*1",
    r"max_replicas\s*=\s*3",
)

ACA_PROBE_PATTERNS = (
    r'liveness_probe\s+\{[^}]*path\s*=\s*"/health/live"[^}]*port\s*=\s*8000',
    r'readiness_probe\s+\{[^}]*path\s*=\s*"/health/ready"[^}]*port\s*=\s*8000',
)

ACA_SECURITY_PATTERNS = (
    r"allow_insecure_connections\s*=\s*false",
    r'name\s*=\s*"ENABLE_HSTS"',
    r'value\s*=\s*"true"',
    r"validation\s+\{",
)

FORBIDDEN_ACA_SECRET_PATTERNS = (
    r"secret\s+\{[^}]*value\s*=",
    r"password_secret_name\s*=",
    r"azurerm_key_vault_secret",
)

TASK18_ACA_IDENTITY_PATTERNS = (
    r"identity\s+\{",
    r'type\s*=\s*"SystemAssigned, UserAssigned"',
)

TASK18_RBAC_PATTERNS = (
    r'resource\s+"azurerm_role_assignment"\s+"aca_acr_pull"',
    r'role_definition_name\s*=\s*"AcrPull"',
    r'resource\s+"azurerm_role_assignment"\s+"aca_key_vault_secrets_user"',
    r'role_definition_name\s*=\s*"Key Vault Secrets User"',
    r"azurerm_container_app\.weather_api\.identity\[0\]\.principal_id",
)

ACR_SECURITY_PATTERNS = (
    r"admin_enabled\s*=\s*false",
    r'resource\s+"azurerm_container_registry"\s+"prod"',
)

KEY_VAULT_SECURITY_PATTERNS = (
    r"rbac_authorization_enabled\s*=\s*true",
    r'resource\s+"azurerm_key_vault"\s+"prod"',
)

KEY_VAULT_DATA_PLANE_HARDENING_PATTERNS = (
    r"enabled_for_deployment\s*=\s*false",
    r"enabled_for_template_deployment\s*=\s*false",
    r"enabled_for_disk_encryption\s*=\s*false",
    r"network_acls\s+\{",
    r'default_action\s*=\s*length\(var\.key_vault_allowed_ip_ranges\)\s*>\s*0\s*\?\s*"Deny"\s*:\s*"Allow"',
)

FORBIDDEN_LEGACY_KV_PATTERNS = (
    r'resource\s+"azurerm_key_vault_access_policy"',
    r"enable_rbac_authorization\s*=\s*false",
)

FORBIDDEN_ACR_SECRET_OUTPUTS = (
    "admin_password",
    "admin_username",
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
    terraform_dir = PROD_DIR / ".terraform"
    if terraform_dir.is_dir():
        shutil.rmtree(terraform_dir)
    init = _run_terraform("init", "-backend=false", "-reconfigure")
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
    """Locals and RG resource match CONTEXT naming (defaults → rg-cad-prod-uksouth)."""
    main_tf = PROD_DIR / "main.tf"
    assert main_tf.is_file()
    contents = main_tf.read_text(encoding="utf-8")
    assert "rg-${var.prefix}-${var.environment}-${var.location}" in contents
    assert re.search(r'resource\s+"azurerm_resource_group"\s+"prod"', contents)


def test_prod_stack_core_resource_locals_match_context() -> None:
    """Naming locals resolve to CONTEXT defaults: acrcadprod, kv-cad-prod-uks."""
    main_tf = PROD_DIR / "main.tf"
    contents = main_tf.read_text(encoding="utf-8")
    assert 'acr_name       = "acr${var.prefix}${var.environment}"' in contents
    assert 'key_vault_name = "kv-${var.prefix}-${var.environment}-uks"' in contents
    assert CONTEXT_ACR_NAME == "acrcadprod"
    assert CONTEXT_KEY_VAULT_NAME == "kv-cad-prod-uks"


def test_prod_stack_declares_acr_with_context_name() -> None:
    """ACR uses naming local and disables admin user (AcrPull-only path)."""
    acr_tf = PROD_DIR / "acr.tf"
    main_tf = PROD_DIR / "main.tf"
    assert acr_tf.is_file(), "infra/envs/prod/acr.tf must exist"
    contents = acr_tf.read_text(encoding="utf-8") + main_tf.read_text(encoding="utf-8")
    assert "local.acr_name" in acr_tf.read_text(encoding="utf-8")
    for pattern in ACR_SECURITY_PATTERNS:
        assert re.search(pattern, contents), f"missing ACR setting: {pattern!r}"


def test_prod_stack_declares_key_vault_rbac_ready() -> None:
    """Key Vault uses naming local, RBAC auth, and no OpenWeatherMap secret in Terraform."""
    keyvault_tf = PROD_DIR / "keyvault.tf"
    variables_tf = PROD_DIR / "variables.tf"
    assert keyvault_tf.is_file(), "infra/envs/prod/keyvault.tf must exist"
    contents = keyvault_tf.read_text(encoding="utf-8") + variables_tf.read_text(encoding="utf-8")
    assert "local.key_vault_name" in keyvault_tf.read_text(encoding="utf-8")
    for pattern in KEY_VAULT_SECURITY_PATTERNS:
        assert re.search(pattern, contents), f"missing Key Vault setting: {pattern!r}"
    for pattern in KEY_VAULT_DATA_PLANE_HARDENING_PATTERNS:
        assert re.search(pattern, contents), f"missing Key Vault hardening: {pattern!r}"
    for pattern in FORBIDDEN_LEGACY_KV_PATTERNS:
        assert not re.search(pattern, contents), f"forbidden Key Vault pattern: {pattern!r}"
    assert "azurerm_key_vault_secret" not in contents


def test_prod_stack_task16_security_notes_cover_acr_and_key_vault() -> None:
    """security_notes output documents Task 16 ACR/KV controls for operators."""
    outputs_tf = PROD_DIR / "outputs.tf"
    contents = outputs_tf.read_text(encoding="utf-8")
    for key in (
        "acr_admin_disabled",
        "key_vault_rbac",
        "key_vault_secrets_in_tf",
        "key_vault_manual_secret",
    ):
        assert key in contents, f"missing security_notes.{key}"


def test_prod_stack_does_not_export_acr_admin_credentials() -> None:
    """ACR admin is disabled; outputs must not expose admin_username/admin_password."""
    outputs_tf = PROD_DIR / "outputs.tf"
    contents = outputs_tf.read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_ACR_SECRET_OUTPUTS:
        assert forbidden not in contents, f"outputs.tf must not reference {forbidden!r}"


def test_prod_stack_outputs_core_azure_resource_names() -> None:
    """Outputs expose RG, ACR, and Key Vault names for operators and downstream tasks."""
    outputs_tf = PROD_DIR / "outputs.tf"
    contents = outputs_tf.read_text(encoding="utf-8")
    for name in ("acr_name", "key_vault_name", "key_vault_id", "acr_login_server"):
        assert re.search(rf'output\s+"{re.escape(name)}"\s+\{{', contents), (
            f'missing output "{name}" in outputs.tf'
        )
    assert "azurerm_container_registry.prod.name" in contents
    assert "azurerm_key_vault.prod" in contents


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


def test_prod_stack_declares_aca_environment_and_container_app() -> None:
    """Task 17: ACA env + app with CONTEXT names, public ingress, scale bounds, health probes."""
    aca_tf = PROD_DIR / "aca.tf"
    main_tf = PROD_DIR / "main.tf"
    assert aca_tf.is_file(), "infra/envs/prod/aca.tf must exist"
    aca_contents = aca_tf.read_text(encoding="utf-8")
    main_contents = main_tf.read_text(encoding="utf-8")
    cae_local = 'cae_name       = "cae-${var.prefix}-${var.environment}-${var.location}"'
    assert cae_local in main_contents
    assert 'container_app_name = "ca-weather-api-${var.environment}"' in main_contents
    assert CONTEXT_CAE_NAME == "cae-cad-prod-uksouth"
    assert CONTEXT_CONTAINER_APP_NAME == "ca-weather-api-prod"
    assert "local.cae_name" in aca_contents
    assert "local.container_app_name" in aca_contents
    for pattern in ACA_RESOURCE_PATTERNS:
        assert re.search(pattern, aca_contents), f"missing ACA resource: {pattern!r}"
    for pattern in ACA_INGRESS_AND_SCALE_PATTERNS:
        assert re.search(pattern, aca_contents), f"missing ACA ingress/scale: {pattern!r}"
    for pattern in ACA_PROBE_PATTERNS:
        assert re.search(pattern, aca_contents, re.DOTALL), f"missing ACA probe: {pattern!r}"


def test_prod_stack_outputs_aca_ingress_fqdn() -> None:
    """Task 17: outputs expose ACA ingress FQDN for operators and README live URL."""
    outputs_tf = PROD_DIR / "outputs.tf"
    contents = outputs_tf.read_text(encoding="utf-8")
    assert re.search(r'output\s+"container_app_fqdn"\s+\{', contents), (
        'missing output "container_app_fqdn" in outputs.tf'
    )
    assert "azurerm_container_app.weather_api.latest_revision_fqdn" in contents
    assert re.search(r'output\s+"container_app_name"\s+\{', contents)
    assert re.search(r'output\s+"container_app_environment_name"\s+\{', contents)


def test_prod_stack_aca_security_contract() -> None:
    """Task 17: ACA skeleton has HTTPS-only ingress, HSTS env, no secrets in Terraform."""
    aca_tf = PROD_DIR / "aca.tf"
    outputs_tf = PROD_DIR / "outputs.tf"
    aca_contents = aca_tf.read_text(encoding="utf-8")
    notes_contents = outputs_tf.read_text(encoding="utf-8")
    for pattern in ACA_SECURITY_PATTERNS:
        assert re.search(pattern, aca_contents), f"missing ACA security setting: {pattern!r}"
    for pattern in FORBIDDEN_ACA_SECRET_PATTERNS:
        assert not re.search(pattern, aca_contents), f"forbidden ACA pattern: {pattern!r}"
    for key in ("aca_ingress_https_only", "aca_secrets_in_tf", "aca_hsts"):
        assert key in notes_contents, f"missing security_notes.{key}"


def test_prod_stack_aca_runtime_identity_and_acr_pull() -> None:
    """Task 18: system-assigned MI on ACA and AcrPull RBAC (no ACR admin)."""
    aca_tf = PROD_DIR / "aca.tf"
    rbac_tf = PROD_DIR / "rbac.tf"
    acr_tf = PROD_DIR / "acr.tf"
    assert rbac_tf.is_file(), "infra/envs/prod/rbac.tf must exist"
    aca_contents = aca_tf.read_text(encoding="utf-8")
    rbac_contents = rbac_tf.read_text(encoding="utf-8")
    acr_contents = acr_tf.read_text(encoding="utf-8")
    for pattern in TASK18_ACA_IDENTITY_PATTERNS:
        assert re.search(pattern, aca_contents), f"missing ACA identity: {pattern!r}"
    for pattern in TASK18_RBAC_PATTERNS:
        assert re.search(pattern, rbac_contents), f"missing runtime RBAC: {pattern!r}"
    assert re.search(r"admin_enabled\s*=\s*false", acr_contents)
    assert "azurerm_container_registry.prod.id" in rbac_contents


def test_prod_stack_aca_weather_provider_and_kv_secret_ref() -> None:
    """Task 18: prod provider mode and OPENWEATHERMAP_API_KEY via Key Vault ref (no value in TF)."""
    aca_tf = PROD_DIR / "aca.tf"
    keyvault_tf = PROD_DIR / "keyvault.tf"
    aca_contents = aca_tf.read_text(encoding="utf-8")
    kv_contents = keyvault_tf.read_text(encoding="utf-8")
    assert re.search(
        r'name\s*=\s*"WEATHER_PROVIDER"[^}]*value\s*=\s*"openweathermap"',
        aca_contents,
        re.DOTALL,
    ), "missing WEATHER_PROVIDER=openweathermap env"
    assert re.search(
        r'name\s*=\s*"OPENWEATHERMAP_API_KEY"[^}]*secret_name\s*=\s*"openweathermap-api-key"',
        aca_contents,
        re.DOTALL,
    ), "missing OPENWEATHERMAP_API_KEY env secret ref"
    assert 'name                = "openweathermap-api-key"' in aca_contents
    kv_secret_ref = 'trim(azurerm_key_vault.prod.vault_uri, "/")}/secrets/openweathermap-api-key'
    assert kv_secret_ref in aca_contents
    assert re.search(r'identity\s*=\s*"System"', aca_contents)
    assert "azurerm_key_vault_secret" not in kv_contents + aca_contents
    for pattern in FORBIDDEN_ACA_SECRET_PATTERNS:
        assert not re.search(pattern, aca_contents), f"forbidden ACA secret pattern: {pattern!r}"


def test_prod_stack_declares_github_ci_identity() -> None:
    """Task 19: CI user-assigned identity id-cad-github-prod for GitHub Actions OIDC."""
    github_oidc_tf = PROD_DIR / "github_oidc.tf"
    assert github_oidc_tf.is_file(), "infra/envs/prod/github_oidc.tf must exist"
    contents = github_oidc_tf.read_text(encoding="utf-8")
    for pattern in TASK19_GITHUB_IDENTITY_PATTERNS:
        assert re.search(pattern, contents), f"missing GitHub CI identity: {pattern!r}"


def test_prod_stack_github_oidc_federated_credential_main_only() -> None:
    """Task 19: federated trust limited to main branch on DNBLabs/containerized-api-deployment."""
    github_oidc_tf = PROD_DIR / "github_oidc.tf"
    oidc_contents = github_oidc_tf.read_text(encoding="utf-8")
    for pattern in TASK19_FEDERATED_CREDENTIAL_PATTERNS:
        assert re.search(pattern, oidc_contents), f"missing federated credential: {pattern!r}"
    assert 'default     = "DNBLabs"' in oidc_contents
    assert 'default     = "containerized-api-deployment"' in oidc_contents
    assert 'strcontains(lower(var.github_organization), "pull_request")' in oidc_contents
    assert "local.github_federated_subject" in oidc_contents


def test_prod_stack_github_ci_rg_contributor_rbac() -> None:
    """Task 19: CI identity Contributor on prod resource group only (not subscription-wide)."""
    github_oidc_tf = PROD_DIR / "github_oidc.tf"
    contents = github_oidc_tf.read_text(encoding="utf-8")
    for pattern in TASK19_CI_RBAC_PATTERNS:
        assert re.search(pattern, contents), f"missing CI RBAC: {pattern!r}"
    assert "azurerm_subscription" not in contents


def test_prod_stack_github_oidc_outputs_without_secrets() -> None:
    """Task 19: expose CI client_id for workflows; never client secrets in Terraform outputs."""
    outputs_tf = PROD_DIR / "outputs.tf"
    github_oidc_tf = PROD_DIR / "github_oidc.tf"
    outputs_contents = outputs_tf.read_text(encoding="utf-8")
    oidc_contents = github_oidc_tf.read_text(encoding="utf-8")
    assert re.search(r'output\s+"github_ci_client_id"\s+\{', outputs_contents)
    assert "azurerm_user_assigned_identity.github_ci.client_id" in outputs_contents
    for forbidden in FORBIDDEN_GITHUB_OIDC_OUTPUTS:
        assert forbidden not in outputs_contents, f"outputs.tf must not reference {forbidden!r}"
        assert forbidden not in oidc_contents, f"github_oidc.tf must not reference {forbidden!r}"
    assert "ci_rbac_future" not in outputs_contents
    assert "ci_rbac" in outputs_contents


def test_prod_stack_github_oidc_security_contract() -> None:
    """Task 19: OIDC federation and CI RBAC meet CONTEXT security boundaries."""
    github_oidc_tf = PROD_DIR / "github_oidc.tf"
    outputs_tf = PROD_DIR / "outputs.tf"
    oidc_contents = github_oidc_tf.read_text(encoding="utf-8")
    notes_contents = outputs_tf.read_text(encoding="utf-8")
    assert oidc_contents.count('resource "azurerm_federated_identity_credential"') == 1
    assert "local.github_federated_subject" in oidc_contents
    assert ':ref:refs/heads/main"' in oidc_contents
    for pattern in TASK19_FORBIDDEN_OIDC_PATTERNS:
        assert not re.search(pattern, oidc_contents), f"forbidden GitHub OIDC pattern: {pattern!r}"
    security_note_keys = (
        "ci_rbac",
        "ci_oidc_federation",
        "ci_oidc_no_static_credentials",
        "ci_contributor_scope_v1",
    )
    for key in security_note_keys:
        assert key in notes_contents, f"missing security_notes.{key}"
