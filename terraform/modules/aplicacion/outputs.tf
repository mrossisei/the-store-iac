output "services" {
  description = "Microservicios desplegados."
  value       = keys(local.services)
}

output "load_balancer_hostname" {
  description = "Nombre DNS del ALB que publica la tienda."
  value       = try(kubernetes_ingress_v1.ui.status[0].load_balancer[0].ingress[0].hostname, "pendiente")
}
