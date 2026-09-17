output "name" {
  value = var.name
}

output "service_host" {
  description = "Nombre DNS corto del Service (resoluble dentro del namespace)."
  value       = kubernetes_service_v1.this.metadata[0].name
}

output "service_fqdn" {
  description = "FQDN del Service dentro del clúster."
  value       = "${kubernetes_service_v1.this.metadata[0].name}.${var.namespace}.svc.cluster.local"
}

output "url" {
  description = "URL base del servicio para otros pods del namespace."
  value       = "http://${kubernetes_service_v1.this.metadata[0].name}"
}

output "selector_labels" {
  value = local.selector_labels
}
