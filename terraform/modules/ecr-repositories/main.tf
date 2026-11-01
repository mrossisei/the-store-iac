terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}
variable "name" { type = string }
variable "services" { type = map(string) }
resource "aws_ecr_repository" "this" {
  for_each             = var.services
  name                 = "${var.name}/${each.key}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
  encryption_configuration { encryption_type = "AES256" }
  image_scanning_configuration { scan_on_push = true }
}
output "repositories" {
  value = { for service, repo in aws_ecr_repository.this : service => repo.repository_url }
}
