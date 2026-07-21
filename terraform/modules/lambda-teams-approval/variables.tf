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

variable "tags" {
  type        = map(string)
  description = "Tags applied to created resources"
  default     = {}
}
