# Input variables for the bootstrap stack (ADR 0001).

variable "location" {
  type        = string
  description = "Azure region for Terraform remote state resources."
  default     = "uksouth"
}

variable "prefix" {
  type        = string
  description = "Short project prefix used in resource names (CONTEXT: cad)."
  default     = "cad"

  validation {
    condition     = can(regex("^[a-z0-9]{2,8}$", var.prefix))
    error_message = "prefix must be 2-8 lowercase alphanumeric characters."
  }
}

variable "storage_account_name" {
  type        = string
  description = "Globally unique storage account name for remote state. Override if the default is taken."
  default     = "stcadprodtf"

  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "storage_account_name must be 3-24 lowercase alphanumeric characters."
  }
}

variable "container_name" {
  type        = string
  description = "Blob container that holds main-stack Terraform state files."
  default     = "tfstate"

  validation {
    condition     = can(regex("^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", var.container_name))
    error_message = "container_name must be a valid Azure blob container name."
  }
}

variable "state_key" {
  type        = string
  description = "Blob key for the production main-stack state file."
  default     = "prod.terraform.tfstate"
}

variable "blob_delete_retention_days" {
  type        = number
  description = "Soft-delete retention for state blobs (recovery window)."
  default     = 7

  validation {
    condition     = var.blob_delete_retention_days >= 1 && var.blob_delete_retention_days <= 365
    error_message = "blob_delete_retention_days must be between 1 and 365."
  }
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to bootstrap resources."
  default = {
    project     = "containerized-api-deployment"
    environment = "bootstrap"
    managed_by  = "terraform"
  }
}
