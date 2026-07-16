terraform {
  required_version = ">= 1.6.0"

  cloud {
    workspaces {
      name = "dev-portal-s3-dev"
    }
  }
}
