# Production stack skeleton — resources added in Tasks 16–19.

data "azurerm_client_config" "current" {}

locals {
  resource_group_name = "rg-${var.prefix}-${var.environment}-${var.location}"
}
