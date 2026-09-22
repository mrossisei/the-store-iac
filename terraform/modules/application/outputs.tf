output "services" {
  description = "Microservicios desplegados."
  value       = keys(local.services)
}

output "url" {
  description = "Direccion de la tienda."
  value       = "http://${var.hostname}"
}
