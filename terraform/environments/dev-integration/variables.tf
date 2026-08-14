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

variable "aws_region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

variable "github_token" {
  type        = string
  description = "GitHub PAT for S3 gitRef branch validation (repo read)"
  sensitive   = true
}

variable "github_org" {
  type        = string
  description = "GitHub organization or user"
  default     = "PriyaRudroju"
}

variable "github_repo" {
  type        = string
  description = "GitHub repository name"
  default     = "devportal-self-service"
}

variable "git_ref_default" {
  type        = string
  description = "Default Git branch when Port gitRef is empty"
  default     = "dev"
}
