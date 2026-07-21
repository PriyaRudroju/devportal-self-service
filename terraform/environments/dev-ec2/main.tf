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

module "ec2_instance" {
  source = "../../modules/ec2-instance"

  instance_name = var.instance_name
  instance_type = var.instance_type
  tags          = var.tags
}
