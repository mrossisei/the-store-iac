# Raíz de imágenes: repositorios ECR, construcción opcional y selección por digest.
locals {
  environment = jsondecode(file("${path.module}/../../config/entorno.json"))
  releases    = var.release_manifest == null ? {} : jsondecode(file(var.release_manifest)).versions
  selected    = var.app_version == null ? {} : try(local.releases[var.app_version], {})
}

module "repositories" {
  source = "../modules/imagenes"

  name     = local.environment.project
  services = local.environment.services
}

# Construye linux/amd64 y publica con el tag app_version. Requiere un apply previo
# que haya creado los repositorios: el publicador los lee del output repositories.
resource "terraform_data" "publicacion" {
  count = var.build_images ? 1 : 0

  triggers_replace = [var.app_version]

  provisioner "local-exec" {
    working_dir = "${path.module}/../.."
    command     = "python3 scripts/publicar-imagenes.py publish ${var.app_version} --resume"
  }

  depends_on = [module.repositories]
}

data "aws_ecr_image" "selected" {
  for_each = var.app_version == null ? {} : local.environment.services

  repository_name = "${local.environment.project}/${each.key}"
  image_tag       = try(local.selected[each.key].tag, var.app_version)

  depends_on = [module.repositories, terraform_data.publicacion]
}
