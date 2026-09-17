output "environment" {
  value = var.environment
}

output "namespace" {
  value = kubernetes_namespace_v1.this.metadata[0].name
}

output "url" {
  description = "URL HTTP del entorno."
  value       = "http://${var.hostname}${data.terraform_remote_state.platform.outputs.ingress.http_port == 80 ? "" : ":${data.terraform_remote_state.platform.outputs.ingress.http_port}"}"
}

output "https_url" {
  description = "URL HTTPS del entorno (certificado autofirmado) o null si TLS está deshabilitado."
  value       = var.tls_enabled ? "https://${var.hostname}${data.terraform_remote_state.platform.outputs.ingress.https_port == 443 ? "" : ":${data.terraform_remote_state.platform.outputs.ingress.https_port}"}" : null
}

output "images" {
  description = "Imágenes desplegadas por servicio."
  value       = local.images
}

output "persistence" {
  value = var.persistence
}

output "datastores" {
  description = "Endpoints internos de la capa de datos (vacío si persistence = false)."
  value = var.persistence ? {
    catalog_db     = module.catalog_db[0].endpoint
    orders_db      = module.orders_db[0].endpoint
    orders_mq      = module.orders_mq[0].endpoint
    checkout_redis = module.checkout_redis[0].endpoint
    carts_db       = module.carts_db[0].endpoint
  } : {}
}

output "network_policies" {
  description = "Flujos permitidos por las NetworkPolicies (vacío si están deshabilitadas)."
  value       = var.enable_network_policies ? [for f in local.flows : "${f.from} -> ${f.to}:${f.port}"] : []
}
