# Un repositorio ECR por microservicio. Terraform construye cada versión y la
# publica con su tag. Los tags son inmutables: volver a una versión no reconstruye.
locals {
  builds = {
    for pair in setproduct(keys(var.services), var.versions) :
    "${pair[0]}-${pair[1]}" => { service = pair[0], version = pair[1] }
  }
}

resource "aws_ecr_repository" "this" {
  for_each = var.services

  name                 = "${var.name}/${each.key}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "docker_image" "this" {
  for_each = local.builds

  name         = "${aws_ecr_repository.this[each.value.service].repository_url}:${each.value.version}"
  platform     = "linux/amd64"
  keep_locally = true

  build {
    context    = "${var.source_root}/${var.services[each.value.service]}"
    platform   = "linux/amd64"
    build_args = { STORE_VERSION = each.value.version }
  }
}

resource "docker_registry_image" "this" {
  for_each = local.builds

  name          = docker_image.this[each.key].name
  keep_remotely = true
}
