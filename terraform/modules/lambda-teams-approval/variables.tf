variable "function_name" {
  type        = string
  description = "Lambda function name"
  default     = "devportal-teams-approval"
}

variable "lambda_source_path" {
  type        = string
  description = "Path to the Lambda source directory"
}

variable "teams_webhook_url" {
  type        = string
  description = "Microsoft Teams incoming webhook URL"
  sensitive   = true
}

variable "port_client_id" {
  type        = string
  description = "Port.io API client ID"
  sensitive   = true
}

variable "port_client_secret" {
  type        = string
  description = "Port.io API client secret"
  sensitive   = true
}

variable "port_api_url" {
  type        = string
  description = "Port.io API base URL"
  default     = "https://api.port.io"
}

variable "aws_region" {
  type        = string
  description = "AWS region for Lambda and API Gateway"
  default     = "us-east-1"
}

variable "github_token" {
  type        = string
  description = "GitHub PAT for branch existence checks (repo read)"
  sensitive   = true
  default     = ""
}

variable "github_org" {
  type        = string
  description = "GitHub organization or user for branch validation"
}

variable "github_repo" {
  type        = string
  description = "GitHub repository name for branch validation"
}

variable "git_ref_default" {
  type        = string
  description = "Default Git branch when catalog gitRef is empty"
  default     = "dev"
}

variable "servicenow_instance_url" {
  type        = string
  description = "ServiceNow instance base URL, e.g. https://dev123456.service-now.com"
  default     = ""
}

variable "servicenow_username" {
  type        = string
  description = "ServiceNow user for Table and Service Catalog API calls"
  sensitive   = true
  default     = ""
}

variable "servicenow_password" {
  type        = string
  description = "Password for the ServiceNow API user"
  sensitive   = true
  default     = ""
}

variable "servicenow_catalog_item_sys_id" {
  type        = string
  description = "sys_id of the catalog item ordered by the Port form"
  default     = ""
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to created resources"
  default     = {}
}
