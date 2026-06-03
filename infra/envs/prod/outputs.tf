# Outputs for operator verification and downstream documentation (Task 15 skeleton).

output "resource_group_name" {
  description = "Planned production resource group name (created in Task 16)."
  value       = local.resource_group_name
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
  }
}

output "subscription_id" {
  description = "Azure subscription ID for this deployment."
  value       = data.azurerm_client_config.current.subscription_id
}
