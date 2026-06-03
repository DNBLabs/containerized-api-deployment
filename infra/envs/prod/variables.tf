# Input variables for the production main stack (CONTEXT: cad, uksouth).

variable "location" {
  type        = string
  description = "Azure region for production resources."
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

variable "environment" {
  type        = string
  description = "Environment segment in resource names."
  default     = "prod"

  validation {
    condition     = can(regex("^[a-z0-9]{2,12}$", var.environment))
    error_message = "environment must be 2-12 lowercase alphanumeric characters."
  }
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to production resources."
  default = {
    project     = "containerized-api-deployment"
    environment = "prod"
    managed_by  = "terraform"
  }
}
