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
