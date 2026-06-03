# Azure Container Apps environment and tracer API skeleton (Task 17).
# Runtime MI, AcrPull, and Key Vault secret ref wired in Task 18.

locals {
  weather_api_image = "${azurerm_container_registry.prod.login_server}/weather-api:bootstrap"
}

variable "container_image" {
  type        = string
  description = "Container image for ACA; empty uses acrcadprod.azurecr.io/weather-api:bootstrap."
  default     = ""

  validation {
    condition = (
      length(var.container_image) <= 512
      && (var.container_image == "" || (
        length(trimspace(var.container_image)) > 0
        && !can(regex("[\\s;|`$()]", var.container_image))
      ))
    )
    error_message = "container_image must be empty (use default ACR tag) or a valid OCI reference (max 512 chars, no shell metacharacters)."
  }
}

resource "azurerm_container_app_environment" "prod" {
  name                = local.cae_name
  location            = azurerm_resource_group.prod.location
  resource_group_name = azurerm_resource_group.prod.name
  tags                = var.tags
}

resource "azurerm_container_app" "weather_api" {
  name                         = local.container_app_name
  container_app_environment_id = azurerm_container_app_environment.prod.id
  resource_group_name          = azurerm_resource_group.prod.name
  revision_mode                = "Single"

  identity {
    type         = "SystemAssigned, UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aca_acr_pull.id]
  }

  secret {
    name                = "openweathermap-api-key"
    key_vault_secret_id = "${trim(azurerm_key_vault.prod.vault_uri, "/")}/secrets/openweathermap-api-key"
    identity            = "System"
  }

  registry {
    server   = azurerm_container_registry.prod.login_server
    identity = azurerm_user_assigned_identity.aca_acr_pull.id
  }

  depends_on = [
    azurerm_role_assignment.uami_acr_pull,
  ]

  template {
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "weather-api"
      image  = var.container_image != "" ? var.container_image : local.weather_api_image
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "ENABLE_HSTS"
        value = "true"
      }

      env {
        name  = "WEATHER_PROVIDER"
        value = "openweathermap"
      }

      env {
        name        = "OPENWEATHERMAP_API_KEY"
        secret_name = "openweathermap-api-key"
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/health/live"
        port      = 8000
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/health/ready"
        port      = 8000
      }
    }
  }

  ingress {
    external_enabled           = true
    allow_insecure_connections = false
    target_port                = 8000

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.tags
}
