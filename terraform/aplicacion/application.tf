locals {
  environment = jsondecode(file("${path.module}/../../config/entorno.json"))
  # Puede sobrescribirse; por defecto reutiliza el bucket inicializado de esta raíz.
  backend_config  = try(jsondecode(file("${path.module}/.terraform/terraform.tfstate")).backend.config, {})
  state_bucket    = var.state_bucket != null ? var.state_bucket : try(local.backend_config.bucket, null)
  infra           = var.enable_application ? data.terraform_remote_state.infra[0].outputs : null
  selected_images = var.enable_application ? jsondecode(data.external.release[0].result.images) : {}
}
data "terraform_remote_state" "infra" {
  count   = var.enable_application ? 1 : 0
  backend = "s3"
  config = {
    bucket       = local.state_bucket
    key          = local.environment.state_keys.infra
    region       = local.environment.region
    encrypt      = true
    use_lockfile = true
  }
}
data "external" "release" {
  count   = var.enable_application ? 1 : 0
  program = ["python3", "${path.module}/../../scripts/seleccionar-release.py"]
  query   = { app_version = var.app_version, manifest = abspath("${path.module}/../imagenes/releases-aplicacion.json") }
}
data "external" "image_cache" {
  count      = var.enable_application ? 1 : 0
  program    = ["python3", "${path.module}/../../scripts/preparar-imagenes.py", "check-external"]
  query      = { manifest = abspath(var.access_manifest), images = data.external.release[0].result.images }
  depends_on = [data.external.access]
}
module "app_a" {
  source       = "../modules/aplicacion"
  count        = var.enable_application ? 1 : 0
  providers    = { kubernetes = kubernetes.kind_a }
  namespace    = var.namespace
  region       = local.environment.region
  images       = local.selected_images
  databases    = local.infra.databases
  replicas     = var.replicas
  ui_node_port = local.environment.kind.ui_node_port
  depends_on   = [data.external.image_cache]
}
module "app_b" {
  source       = "../modules/aplicacion"
  count        = var.enable_application ? 1 : 0
  providers    = { kubernetes = kubernetes.kind_b }
  namespace    = var.namespace
  region       = local.environment.region
  images       = local.selected_images
  databases    = local.infra.databases
  replicas     = var.replicas
  ui_node_port = local.environment.kind.ui_node_port
  depends_on   = [data.external.image_cache]
}
