terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

module "s3_bucket" {
  source = "git::https://github.com/PriyaRudroju/developer-self-service.git//terraform/modules/s3-bucket?ref=main"
  bucket_name = var.bucket_name
  tags        = var.tags
}
