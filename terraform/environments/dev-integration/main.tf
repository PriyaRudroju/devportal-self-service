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
  github_token       = var.github_token
  github_org         = var.github_org
  github_repo        = var.github_repo
  git_ref_default    = var.git_ref_default

  servicenow_instance_url        = var.servicenow_instance_url
  servicenow_username            = var.servicenow_username
  servicenow_password            = var.servicenow_password
  servicenow_catalog_item_sys_id = var.servicenow_catalog_item_sys_id

  tags = {
    Project     = "devportal-self-service"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}
