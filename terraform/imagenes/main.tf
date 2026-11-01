locals {
  environment = jsondecode(file("${path.module}/../../config/entorno.json"))
  releases    = var.release_manifest == null ? {} : jsondecode(file(var.release_manifest)).versions
  selected    = var.app_version == null ? {} : try(local.releases[var.app_version], {})
}
module "repositories" {
  source   = "../modules/ecr-repositories"
  name     = local.environment.project
  services = local.environment.services
}
variable "release_manifest" {
  description = "Ruta del manifest generado por publicar-imagenes.py; null permite crear sólo repositorios."
  type        = string
  default     = null
}
variable "app_version" {
  description = "Sólo selecciona una publicación existente; nunca construye ni publica."
  type        = string
  default     = null
  validation {
    condition     = var.app_version == null ? true : contains(["v1", "v2"], var.app_version)
    error_message = "app_version debe ser v1 o v2."
  }
}
data "aws_ecr_image" "selected" {
  for_each        = var.app_version == null ? {} : local.environment.services
  repository_name = "${local.environment.project}/${each.key}"
  image_tag       = var.app_version
  depends_on      = [module.repositories]
}
output "repositories" { value = module.repositories.repositories }
output "references" { value = local.releases }
output "images" {
  value = { for service, image in data.aws_ecr_image.selected : service => "${module.repositories.repositories[service]}@${image.image_digest}" }
  precondition {
    condition = var.app_version == null ? true : (
      toset(keys(local.selected)) == toset(keys(local.environment.services)) &&
      alltrue([for service, image in data.aws_ecr_image.selected : try(
        local.selected[service].digest == image.image_digest &&
        local.selected[service].platform == "linux/amd64" &&
      local.selected[service].repository == module.repositories.repositories[service], false)])
    )
    error_message = "Publicación incompleta, plataforma incorrecta o digest/repositorio diferente de ECR."
  }
}
