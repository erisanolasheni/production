terraform {
  required_version = ">= 1.0"

  # Configure with -backend-config=backend.hcl (see backend.example.hcl).
  # Required for GitHub Actions; use the same file locally after migrating state.
  backend "s3" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}
