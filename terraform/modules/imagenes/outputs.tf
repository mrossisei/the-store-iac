output "images" {
  description = "Referencia completa de cada imagen publicada."
  value       = { for name, image in docker_registry_image.this : name => image.name }
}
