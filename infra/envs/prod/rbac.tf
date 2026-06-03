# Runtime RBAC for ACA managed identities (Task 18).
# UAMI + AcrPull exists before container app so the first revision can pull from ACR.

resource "azurerm_user_assigned_identity" "aca_acr_pull" {
  name                = "id-cad-aca-acr-prod"
  resource_group_name = azurerm_resource_group.prod.name
  location            = azurerm_resource_group.prod.location
  tags                = var.tags
}

resource "azurerm_role_assignment" "uami_acr_pull" {
  scope                = azurerm_container_registry.prod.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.aca_acr_pull.principal_id
}

resource "azurerm_role_assignment" "aca_acr_pull" {
  scope                = azurerm_container_registry.prod.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.weather_api.identity[0].principal_id
}

resource "azurerm_role_assignment" "aca_key_vault_secrets_user" {
  scope                = azurerm_key_vault.prod.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_container_app.weather_api.identity[0].principal_id
}
