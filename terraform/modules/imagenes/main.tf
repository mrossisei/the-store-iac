# ---------------------------------------------------------------------------
# Imagenes de los microservicios.
#
# Un repositorio ECR por servicio. Las imagenes se construyen en la maquina a
# partir del codigo fuente de la aplicacion y se publican en ECR; los nodos del
# cluster las descargan con el permiso de lectura que EKS les da por defecto.
# El tag es la variable app_version: cambiarla reconstruye, publica y dispara
# un rolling update.
# ---------------------------------------------------------------------------
terraform {
  required_providers {
    aws    = { source = "hashicorp/aws" }
    docker = { source = "kreuzwerker/docker" }
  }
}

resource "aws_ecr_repository" "this" {
  for_each = var.services

  name                 = "${var.name}/${each.key}"
  image_tag_mutability = "MUTABLE"
  # Permite borrar el repositorio con imagenes adentro en el destroy.
  force_delete = true
}

resource "docker_image" "this" {
  for_each = var.services

  name     = "${aws_ecr_repository.this[each.key].repository_url}:${var.app_version}"
  platform = "linux/amd64"

  build {
    context  = "${var.source_root}/${each.value}"
    platform = "linux/amd64"
  }
}

resource "docker_registry_image" "this" {
  for_each = var.services

  name          = docker_image.this[each.key].name
  keep_remotely = true

  triggers = {
    image_id = docker_image.this[each.key].image_id
  }
}
