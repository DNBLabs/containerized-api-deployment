# Outputs for operator verification and downstream documentation (Tasks 15–19).

output "resource_group_name" {
  description = "Production resource group name."
  value       = azurerm_resource_group.prod.name
}

output "acr_name" {
  description = "Azure Container Registry name (CONTEXT: acrcadprod)."
  value       = azurerm_container_registry.prod.name
}

output "acr_login_server" {
  description = "ACR login server hostname for docker push and ACA image refs."
  value       = azurerm_container_registry.prod.login_server
}

output "key_vault_name" {
  description = "Key Vault name for manual secret provisioning (CONTEXT: kv-cad-prod-uks)."
  value       = azurerm_key_vault.prod.name
}

output "key_vault_id" {
  description = "Key Vault resource ID for RBAC assignments (Tasks 18–19)."
  value       = azurerm_key_vault.prod.id
}

output "container_app_environment_name" {
  description = "Container Apps environment name (CONTEXT: cae-cad-prod-uksouth)."
  value       = azurerm_container_app_environment.prod.name
}

output "container_app_name" {
  description = "Container app name (CONTEXT: ca-weather-api-prod)."
  value       = azurerm_container_app.weather_api.name
}

output "container_app_fqdn" {
  description = "Public HTTPS FQDN for the weather API (ACA default ingress)."
  value       = azurerm_container_app.weather_api.latest_revision_fqdn
}

output "github_ci_client_id" {
  description = "Client ID for id-cad-github-prod (GitHub Actions azure/login OIDC; not a secret)."
  value       = azurerm_user_assigned_identity.github_ci.client_id
}

output "github_ci_identity_name" {
  description = "User-assigned identity name for GitHub Actions (CONTEXT: id-cad-github-prod)."
  value       = azurerm_user_assigned_identity.github_ci.name
}

output "location" {
  description = "Azure region for the production stack."
  value       = var.location
}

output "prefix" {
  description = "Naming prefix for production resources."
  value       = var.prefix
}

output "security_notes" {
  description = "Security checklist for remote state and Terraform operations (no secrets in git)."
  value = {
    remote_state_auth            = "backend.hcl: use_azuread_auth = true only — never access_key"
    provider_storage_auth        = "storage_use_azuread = true in versions.tf"
    backend_config_gitignored    = true
    state_contains_secrets       = true
    operator_rbac_on_state_store = "Storage Blob Data Contributor on bootstrap storage account (least privilege for state blob access)"
    ci_rbac                      = "id-cad-github-prod Contributor on rg-cad-prod-uksouth; grant Storage Blob Data Contributor on state account separately for terraform init/plan/apply"
    ci_oidc_federation           = "repo:DNBLabs/containerized-api-deployment:ref:refs/heads/main only (no client secrets in TF or GitHub)"
    ci_oidc_no_static_credentials = "OIDC only — no long-lived Azure credentials in TF or GitHub"
    ci_contributor_scope_v1      = "RG Contributor accepted for v1 portfolio; tighten to custom roles in future ADR"
    local_init_env_windows       = "ARM_USE_AZUREAD=true before terraform init -backend-config=backend.hcl"
    acr_admin_disabled           = true
    acr_pull_auth                = "ACA system-assigned MI + AcrPull on acrcadprod (no admin user)"
    acr_public_endpoint          = "Basic SKU — public_network_access required for v1 CI push; private endpoint deferred"
    key_vault_rbac               = true
    key_vault_secrets_in_tf      = false
    key_vault_manual_secret      = "openweathermap-api-key in KV (env OPENWEATHERMAP_API_KEY); az keyvault secret set after apply"
    key_vault_network            = length(var.key_vault_allowed_ip_ranges) > 0 ? "Deny default + ip_rules" : "Allow default (RBAC required); set key_vault_allowed_ip_ranges to tighten"
    key_vault_purge_protection   = "disabled for portfolio teardown; enable for long-lived prod if destroy not needed"
    aca_scale                    = "minReplicas=1 maxReplicas=3; no custom scale rules in v1"
    aca_probes                   = "/health/live (liveness), /health/ready (readiness) on port 8000"
    aca_image_placeholder        = "container_image defaults to public MCR quickstart until CI deploy (Tasks 21–22)"
    aca_ingress_https_only       = true
    aca_secrets_in_tf            = false
    aca_hsts                     = "ENABLE_HSTS=true on ACA template (CONTEXT prod)"
    aca_runtime_mi               = "System-assigned on ca-weather-api-prod"
    aca_kv_secret_ref            = "openweathermap-api-key KV ref -> env OPENWEATHERMAP_API_KEY (manual set before ready)"
    aca_weather_provider         = "WEATHER_PROVIDER=openweathermap in prod ACA"
  }
}

output "subscription_id" {
  description = "Azure subscription ID for this deployment."
  value       = data.azurerm_client_config.current.subscription_id
}
