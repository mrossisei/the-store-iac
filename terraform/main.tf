# The Store: red y ALB, imágenes, cómputo, datos y aplicación.
module "red" {
  source = "./modules/red"

  name             = var.project
  region           = var.region
  cidr             = var.vpc_cidr
  zones            = var.zones
  application_port = var.kind.host_ui_port
}

module "imagenes" {
  source = "./modules/imagenes"

  name        = var.project
  services    = var.services
  versions    = var.image_versions
  source_root = "${path.root}/../the-store/src"
}

module "computo" {
  source = "./modules/computo"

  name                          = var.project
  region                        = var.region
  private_subnet_ids            = module.red.private_subnet_ids
  application_security_group_id = module.red.application_security_group_id
  target_group_arn              = module.red.target_group_arn
  instance_profile_name         = var.instance_profile_name
  ami_id                        = var.ami_id
  instance_type                 = var.instance_type
  kind                          = var.kind

  # Las EC2 instalan paquetes al arrancar: necesitan NAT y rutas listos.
  depends_on = [module.red]
}

module "datos" {
  source = "./modules/datos"

  name                          = var.project
  vpc_id                        = module.red.vpc_id
  subnet_ids                    = values(module.red.db_subnet_ids)
  application_security_group_id = module.red.application_security_group_id
  availability_zones            = [for zone in values(var.zones) : zone.availability_zone]
  db_instance_class             = var.db_instance_class
  cache_node_type               = var.cache_node_type
}

# Las EC2 son privadas: este script espera a kind y abre un túnel SSM a cada API.
data "external" "acceso" {
  program = ["bash", "${path.module}/../scripts/acceso-kind.sh", var.region, module.computo.instance_ids.a, module.computo.instance_ids.b]
}

locals {
  images = { for service, repo in module.imagenes.repositories : service => "${repo}:${var.app_version}" }
}

module "app_a" {
  source    = "./modules/aplicacion"
  providers = { kubernetes = kubernetes.kind_a }

  region     = var.region
  images     = local.images
  replicas   = var.replicas
  quarantine = var.quarantine
  databases  = module.datos.connection
  kind       = var.kind

  # Las imágenes tienen que estar publicadas antes de crear los Deployments.
  depends_on = [module.imagenes]
}

module "app_b" {
  source    = "./modules/aplicacion"
  providers = { kubernetes = kubernetes.kind_b }

  region     = var.region
  images     = local.images
  replicas   = var.replicas
  quarantine = var.quarantine
  databases  = module.datos.connection
  kind       = var.kind

  depends_on = [module.imagenes]
}
