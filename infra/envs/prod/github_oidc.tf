# GitHub Actions OIDC federation and CI RBAC (Task 19).
# Federated trust is limited to main on DNBLabs/containerized-api-deployment.

variable "github_organization" {
  type        = string
  description = "GitHub org or user for OIDC federated credential subject (CONTEXT: DNBLabs)."
  default     = "DNBLabs"

  validation {
    condition = (
      can(regex("^[A-Za-z0-9_.-]+$", var.github_organization))
      && length(var.github_organization) <= 39
      && !strcontains(lower(var.github_organization), "pull_request")
      && !strcontains(lower(var.github_organization), "environment")
    )
    error_message = "github_organization must be a plain GitHub org/user slug (no /, :, *, or OIDC subject tokens)."
  }
}

variable "github_repository" {
  type        = string
  description = "GitHub repository name for OIDC federated credential subject."
  default     = "containerized-api-deployment"

  validation {
    condition = (
      can(regex("^[A-Za-z0-9_.-]+$", var.github_repository))
      && length(var.github_repository) <= 100
      && !strcontains(lower(var.github_repository), "pull_request")
      && !strcontains(lower(var.github_repository), "environment")
    )
    error_message = "github_repository must be a plain GitHub repo name (no /, :, *, or OIDC subject tokens)."
  }
}

locals {
  github_federated_subject = "repo:${var.github_organization}/${var.github_repository}:ref:refs/heads/main"
}

resource "azurerm_user_assigned_identity" "github_ci" {
  name                = "id-cad-github-prod"
  resource_group_name = azurerm_resource_group.prod.name
  location            = azurerm_resource_group.prod.location
  tags                = var.tags
}

resource "azurerm_federated_identity_credential" "github_main" {
  name                = "fc-cad-github-main-prod"
  resource_group_name = azurerm_resource_group.prod.name
  parent_id           = azurerm_user_assigned_identity.github_ci.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = local.github_federated_subject
}

resource "azurerm_role_assignment" "github_ci_rg_contributor" {
  scope                = azurerm_resource_group.prod.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.github_ci.principal_id
}
