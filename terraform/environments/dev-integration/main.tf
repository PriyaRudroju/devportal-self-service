terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "teams_approval" {
  source = "../../modules/lambda-teams-approval"

  lambda_source_path = abspath("${path.module}/../../../lambda/teams-approval")
  teams_webhook_url  = var.teams_webhook_url
  port_client_id     = var.port_client_id
  port_client_secret = var.port_client_secret
  aws_region         = var.aws_region

  tags = {
    Project     = "devportal-self-service"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}
