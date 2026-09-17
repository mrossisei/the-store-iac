output "images" {
  description = "Referencia completa (registry/nombre:tag) de cada imagen publicada; la consume la capa 3."
  value       = { for svc, img in docker_registry_image.service : svc => img.name }
}

output "image_tags" {
  description = "Tag (hash del código fuente) de cada servicio."
  value       = local.image_tags
}

output "image_digests" {
  description = "Digest sha256 del manifest publicado en el registry."
  value       = { for svc, img in docker_registry_image.service : svc => img.sha256_digest }
}
