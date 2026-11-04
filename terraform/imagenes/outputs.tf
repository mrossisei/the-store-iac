output "repositories" {
  description = "URL de cada repositorio ECR."
  value       = module.repositories.repositories
}

output "references" {
  description = "Publicaciones registradas en el manifest."
  value       = local.releases
}

output "images" {
  description = "Imagen seleccionada de cada servicio, por digest."
  value       = { for service, image in data.aws_ecr_image.selected : service => "${module.repositories.repositories[service]}@${image.image_digest}" }

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
