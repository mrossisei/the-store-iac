# Raíz de aplicación: los mismos módulos en los dos kind, uno por alias de provider.
# Terraform no admite for_each sobre providers: cada clúster se declara por separado.
locals {
  environment = jsondecode(file("${path.module}/../../config/entorno.json"))

  # Puede sobrescribirse; por defecto reutiliza el bucket inicializado de esta raíz.
  backend_config = try(jsondecode(file("${path.module}/.terraform/terraform.tfstate")).backend.config, {})
  state_bucket   = var.state_bucket != null ? var.state_bucket : try(local.backend_config.bucket, null)

  infra           = var.enable_application ? data.terraform_remote_state.infra[0].outputs : null
  selected_images = var.enable_application ? jsondecode(data.external.release[0].result.images) : {}
}

# --- Kind A ----------------------------------------------------------------
module "app_a" {
  source    = "../modules/aplicacion"
  count     = var.enable_application ? 1 : 0
  providers = { kubernetes = kubernetes.kind_a }

  namespace    = var.namespace
  region       = local.environment.region
  images       = local.selected_images
  databases    = local.infra.databases
  replicas     = var.replicas
  ui_node_port = local.environment.kind.ui_node_port

  depends_on = [data.external.image_cache]
}

module "politicas_a" {
  source    = "../modules/aplicacion/modules/politicas"
  count     = var.enable_application && var.enable_network_policies ? 1 : 0
  providers = { kubernetes = kubernetes.kind_a }

  namespace    = module.app_a[0].namespace
  quarantine   = var.quarantine
  pod_cidr     = local.environment.kind.pod_cidr
  service_cidr = local.environment.kind.service_cidr
}

module "probe_a" {
  source    = "../modules/aplicacion/modules/prueba-acceso"
  count     = var.enable_access_probe ? 1 : 0
  providers = { kubernetes = kubernetes.kind_a }

  cluster_key = "a"
  cluster_uid = data.external.access.result.uid_a
  value       = var.probe_value
}

# --- Kind B ----------------------------------------------------------------
module "app_b" {
  source    = "../modules/aplicacion"
  count     = var.enable_application ? 1 : 0
  providers = { kubernetes = kubernetes.kind_b }

  namespace    = var.namespace
  region       = local.environment.region
  images       = local.selected_images
  databases    = local.infra.databases
  replicas     = var.replicas
  ui_node_port = local.environment.kind.ui_node_port

  depends_on = [data.external.image_cache]
}

module "politicas_b" {
  source    = "../modules/aplicacion/modules/politicas"
  count     = var.enable_application && var.enable_network_policies ? 1 : 0
  providers = { kubernetes = kubernetes.kind_b }

  namespace    = module.app_b[0].namespace
  quarantine   = var.quarantine
  pod_cidr     = local.environment.kind.pod_cidr
  service_cidr = local.environment.kind.service_cidr
}

module "probe_b" {
  source    = "../modules/aplicacion/modules/prueba-acceso"
  count     = var.enable_access_probe ? 1 : 0
  providers = { kubernetes = kubernetes.kind_b }

  cluster_key = "b"
  cluster_uid = data.external.access.result.uid_b
  value       = var.probe_value
}
