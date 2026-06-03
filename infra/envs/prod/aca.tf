# Azure Container Apps environment and tracer API skeleton (Task 17).
# Public placeholder image until CI push (Tasks 21-22); AcrPull + secrets in Task 18.

variable "container_image" {
  type        = string
  description = "Container image for ACA; default public placeholder until CI push (Tasks 21-22)."
  default     = "mcr.microsoft.com/k8se/quickstart:latest"

  validation {
    condition = (
      length(trimspace(var.container_image)) > 0
      && length(var.container_image) <= 512
      && !can(regex("[\\s;|`$()]", var.container_image))
    )
    error_message = "container_image must be a non-empty OCI reference (max 512 chars, no shell metacharacters)."
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

  template {
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "weather-api"
      image  = var.container_image
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "ENABLE_HSTS"
        value = "true"
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
