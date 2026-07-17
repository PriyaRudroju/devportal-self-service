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
  source      = "https://github.com/PriyaRudroju/devportal-self-service/tree/main/terraform/modules/s3-bucket"
  bucket_name = var.bucket_name
  tags        = var.tags
}
