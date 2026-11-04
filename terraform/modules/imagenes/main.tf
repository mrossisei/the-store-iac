# Un repositorio ECR inmutable por microservicio.
resource "aws_ecr_repository" "this" {
  for_each             = var.services
  name                 = "${var.name}/${each.key}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }
}
