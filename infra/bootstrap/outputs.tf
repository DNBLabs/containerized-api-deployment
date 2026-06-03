# Outputs for configuring the main stack azurerm remote backend (Task 15).

output "resource_group_name" {
  description = "Resource group containing the Terraform remote state storage account."
  value       = azurerm_resource_group.tfstate.name
}

output "storage_account_name" {
  description = "Storage account name for the main stack remote backend."
  value       = azurerm_storage_account.tfstate.name
}

output "container_name" {
  description = "Blob container name for Terraform state files."
  value       = azurerm_storage_container.tfstate.name
}

output "state_key" {
  description = "Recommended blob key for the production main-stack state file."
  value       = var.state_key
}

output "subscription_id" {
  description = "Azure subscription ID (for backend configuration and documentation)."
  value       = data.azurerm_client_config.current.subscription_id
}

output "backend_config" {
  description = "Copy-paste azurerm backend settings for infra/envs/prod (after bootstrap apply)."
  value = {
    resource_group_name  = azurerm_resource_group.tfstate.name
    storage_account_name = azurerm_storage_account.tfstate.name
    container_name       = azurerm_storage_container.tfstate.name
    key                  = var.state_key
    use_azuread_auth     = true
  }
}

output "security_notes" {
  description = "Operator checklist: auth model and RBAC for state storage (no secrets in git)."
  value = {
    shared_access_keys_disabled = true
    provider_storage_auth       = "storage_use_azuread = true (required for apply when keys disabled)"
    backend_auth                = "Azure AD (use_azuread_auth = true)"
    required_rbac               = "Storage Blob Data Contributor on this storage account for operator and id-cad-github-prod (Task 19)"
    state_contains_secrets      = true
    network_hardening           = "Public HTTPS endpoint required for v1 CI/OIDC; no anonymous blob access; optional IP/VNet rules deferred"
  }
}
