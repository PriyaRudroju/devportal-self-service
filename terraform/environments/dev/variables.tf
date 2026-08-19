variable "bucket_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "teams_webhook_url" {
  type        = string
  description = "Microsoft Teams incoming webhook URL"
  sensitive   = true
  default     = "https://example.invalid/teams-placeholder"
}

variable "port_client_id" {
  type        = string
  description = "Port.io API client ID"
  sensitive   = true
  default     = ""
}

variable "port_client_secret" {
  type        = string
  description = "Port.io API client secret"
  sensitive   = true
  default     = ""
}

variable "github_token" {
  type        = string
  description = "GitHub PAT for S3 gitRef branch validation (repo read)"
  sensitive   = true
  default     = ""
}

variable "github_org" {
  type        = string
  default     = "PriyaRudroju"
}

variable "github_repo" {
  type        = string
  default     = "devportal-self-service"
}

variable "git_ref_default" {
  type        = string
  default     = "dev"
}

variable "servicenow_instance_url" {
  type        = string
  description = "ServiceNow instance base URL"
  default     = ""
}

variable "servicenow_username" {
  type        = string
  sensitive   = true
  default     = ""
}

variable "servicenow_password" {
  type        = string
  sensitive   = true
  default     = ""
}

variable "servicenow_catalog_item_sys_id" {
  type        = string
  default     = ""
}
