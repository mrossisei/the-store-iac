output "host" {
  description = "Nombre DNS corto del datastore dentro del namespace."
  value       = kubernetes_service_v1.this.metadata[0].name
}

output "port" {
  value = var.port
}

output "endpoint" {
  description = "host:puerto"
  value       = "${kubernetes_service_v1.this.metadata[0].name}:${var.port}"
}

output "secret_name" {
  description = "Nombre del Secret con las credenciales (para que los consumidores lo referencien)."
  value       = kubernetes_secret_v1.this.metadata[0].name
}

output "selector_labels" {
  value = local.selector_labels
}
