# Outputs for operator verification and downstream documentation (Tasks 15–16).

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
    ci_rbac_future               = "Task 19: id-cad-github-prod scoped to rg-cad-prod-uksouth; separate Blob Data Contributor on state account for terraform init/plan/apply"
    local_init_env_windows       = "ARM_USE_AZUREAD=true before terraform init -backend-config=backend.hcl"
    acr_admin_disabled           = true
    acr_pull_auth                = "Task 18: AcrPull via ACA system-assigned MI only (no admin credentials)"
    acr_public_endpoint          = "Basic SKU — public_network_access required for v1 CI push; private endpoint deferred"
    key_vault_rbac               = true
    key_vault_secrets_in_tf      = false
    key_vault_manual_secret      = "OPENWEATHERMAP_API_KEY via az keyvault secret set after apply (never in git/CI logs)"
    key_vault_network            = length(var.key_vault_allowed_ip_ranges) > 0 ? "Deny default + ip_rules" : "Allow default (RBAC required); set key_vault_allowed_ip_ranges to tighten"
    key_vault_purge_protection   = "disabled for portfolio teardown; enable for long-lived prod if destroy not needed"
  }
}

output "subscription_id" {
  description = "Azure subscription ID for this deployment."
  value       = data.azurerm_client_config.current.subscription_id
}
