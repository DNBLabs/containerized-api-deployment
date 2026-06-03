# Azure Container Registry for immutable weather-api images (Task 16).
# Basic SKU: public endpoint required for v1 GitHub OIDC push (Task 21); admin user disabled.

resource "azurerm_container_registry" "prod" {
  name                = local.acr_name
  resource_group_name = azurerm_resource_group.prod.name
  location            = azurerm_resource_group.prod.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = var.tags
}
