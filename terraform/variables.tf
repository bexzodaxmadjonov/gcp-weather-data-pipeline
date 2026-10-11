variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region for all resources"
  default     = "europe-west1"
}

variable "env" {
  type        = string
  description = "Environment name"
  default     = "dev"

  validation {
    condition     = contains(["dev", "stg", "prod"], var.env)
    error_message = "env must be one of: dev, stg, prod."
  }
}

variable "owner" {
  type        = string
  description = "Owner label applied to resources"
}

variable "bucket_name" {
  type        = string
  description = "Globally unique GCS bucket name"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9_-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "Bucket name must be 3-63 chars: lowercase letters, digits, - or _."
  }
}

variable "bq_dataset_id" {
  type    = string
  default = "weather"
}

variable "locations" {
  type        = list(string)
  description = "Locations the function will fetch weather for"
  default     = ["london"]
}

variable "weather_api_key" {
  type        = string
  sensitive   = true
  description = "tomorrow.io API key"
}