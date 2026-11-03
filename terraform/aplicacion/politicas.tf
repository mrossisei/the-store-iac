locals {
  policies_environment = jsondecode(file("${path.module}/../../config/entorno.json"))
}

module "politicas_a" {
  source       = "../modules/politicas-kind"
  count        = var.enable_application && var.enable_network_policies ? 1 : 0
  providers    = { kubernetes = kubernetes.kind_a }
  namespace    = module.app_a[0].namespace
  quarantine   = var.quarantine
  pod_cidr     = local.policies_environment.kind.pod_cidr
  service_cidr = local.policies_environment.kind.service_cidr
}

module "politicas_b" {
  source       = "../modules/politicas-kind"
  count        = var.enable_application && var.enable_network_policies ? 1 : 0
  providers    = { kubernetes = kubernetes.kind_b }
  namespace    = module.app_b[0].namespace
  quarantine   = var.quarantine
  pod_cidr     = local.policies_environment.kind.pod_cidr
  service_cidr = local.policies_environment.kind.service_cidr
}
