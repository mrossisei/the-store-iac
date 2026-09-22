output "services" {
  description = "Microservicios desplegados."
  value       = keys(local.services)
}
