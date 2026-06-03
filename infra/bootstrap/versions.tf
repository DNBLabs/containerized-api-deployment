# Terraform and provider version constraints for the Day-0 bootstrap stack.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  # Required when shared_access_key_enabled = false — provider must use Entra ID for data-plane polls.
  storage_use_azuread = true

  features {}
}
