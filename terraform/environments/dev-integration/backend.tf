terraform {
  required_version = ">= 1.6.0"

  cloud {
    workspaces {
      name = "dev-portal-integration-dev"
    }
  }
}
