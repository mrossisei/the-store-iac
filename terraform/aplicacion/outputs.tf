output "clusters" {
  description = "Identidades comprobadas por SSM, TLS y API; no contiene credenciales."
  value = {
    a = { context = data.external.access.result.context_a, uid = data.external.access.result.uid_a }
    b = { context = data.external.access.result.context_b, uid = data.external.access.result.uid_b }
  }
}
output "application" {
  value = var.enable_application ? {
    app_version = var.app_version
    images      = local.selected_images
    replicas    = var.replicas
    namespace   = var.namespace
    url         = local.infra.url
  } : null
}
