# T08 agregará los servicios de aplicación utilizando estos mismos aliases.
module "probe_a" {
  source      = "../modules/prueba-acceso"
  count       = var.enable_access_probe ? 1 : 0
  providers   = { kubernetes = kubernetes.kind_a }
  cluster_key = "a"
  cluster_uid = data.external.access.result.uid_a
  value       = var.probe_value
}

module "probe_b" {
  source      = "../modules/prueba-acceso"
  count       = var.enable_access_probe ? 1 : 0
  providers   = { kubernetes = kubernetes.kind_b }
  cluster_key = "b"
  cluster_uid = data.external.access.result.uid_b
  value       = var.probe_value
}
