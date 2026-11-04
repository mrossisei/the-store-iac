output "url" {
  description = "Dirección pública de la tienda."
  value       = "http://${module.red.alb_dns_name}"
}

output "app_version" {
  description = "Versión desplegada."
  value       = var.app_version
}
