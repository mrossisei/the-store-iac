terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "= 6.66.0" }
  }
  backend "s3" {}
}
provider "aws" {
  region = local.environment.region
  default_tags {
    tags = { Project = local.environment.project, ManagedBy = "terraform", Stack = "imagenes" }
  }
}
