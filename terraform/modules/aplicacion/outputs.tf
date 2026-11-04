output "services" {
  description = "Microservicios desplegados."
  value       = keys(local.services)
}

output "namespace" {
  description = "Namespace de la aplicación."
  value       = kubernetes_namespace_v1.this.metadata[0].name
}

output "images" {
  description = "Imagen de cada microservicio."
  value       = var.images
}

output "ui_node_port" {
  description = "NodePort de la UI."
  value       = var.ui_node_port
}
