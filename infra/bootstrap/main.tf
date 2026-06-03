# Day-0 resources: resource group, storage account, and blob container for remote state.

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "tfstate" {
  name     = "rg-${var.prefix}-tfstate-${var.location}"
  location = var.location
  tags     = var.tags
}

resource "azurerm_storage_account" "tfstate" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.tfstate.name
  location                 = azurerm_resource_group.tfstate.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false

  # Secrets: no account keys in backend config; main stack uses Entra ID (see backend_config output).
  shared_access_key_enabled = false

  # Encryption at rest (platform-managed keys; CMK deferred to v1.1).
  infrastructure_encryption_enabled = true
  cross_tenant_replication_enabled  = false

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = var.blob_delete_retention_days
    }
  }

  tags = var.tags
}

resource "azurerm_storage_container" "tfstate" {
  name                  = var.container_name
  storage_account_id    = azurerm_storage_account.tfstate.id
  container_access_type = "private"
}
