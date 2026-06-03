# Key Vault for runtime secrets; upstream API key set manually post-apply (Task 16).

variable "key_vault_allowed_ip_ranges" {
  type        = list(string)
  description = "Optional CIDRs for operator Key Vault data-plane access. When non-empty, network default_action is Deny except listed IPs and AzureServices bypass."
  default     = []

  validation {
    condition = alltrue([
      for cidr in var.key_vault_allowed_ip_ranges : can(cidrhost(cidr, 0))
    ])
    error_message = "Each key_vault_allowed_ip_ranges entry must be a valid IPv4/IPv6 CIDR."
  }
}

resource "azurerm_key_vault" "prod" {
  name                = local.key_vault_name
  location            = azurerm_resource_group.prod.location
  resource_group_name = azurerm_resource_group.prod.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  enabled_for_deployment          = false
  enabled_for_template_deployment = false
  enabled_for_disk_encryption     = false

  network_acls {
    bypass         = "AzureServices"
    default_action = length(var.key_vault_allowed_ip_ranges) > 0 ? "Deny" : "Allow"
    ip_rules       = var.key_vault_allowed_ip_ranges
  }

  tags = var.tags
}
