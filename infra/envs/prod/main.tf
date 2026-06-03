# Production resource group and shared naming locals (Task 16).

data "azurerm_client_config" "current" {}

locals {
  resource_group_name = "rg-${var.prefix}-${var.environment}-${var.location}"
  # Default vars → rg-cad-prod-uksouth, acrcadprod, kv-cad-prod-uks (uks = uksouth short segment).
  acr_name       = "acr${var.prefix}${var.environment}"
  key_vault_name = "kv-${var.prefix}-${var.environment}-uks"
  cae_name       = "cae-${var.prefix}-${var.environment}-${var.location}"
  container_app_name = "ca-weather-api-${var.environment}"
}

resource "azurerm_resource_group" "prod" {
  name     = local.resource_group_name
  location = var.location
  tags     = var.tags
}
