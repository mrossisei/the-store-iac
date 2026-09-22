# ---------------------------------------------------------------------------
# The Store - Infraestructura como Codigo con Terraform sobre AWS
# TP Especial de Redes de Informacion - ITBA
#
# Este archivo orquesta los cinco modulos de la solucion:
#   red        -> VPC, subredes publicas, privadas y de datos, Internet y NAT Gateways, VPC Endpoints
#   cluster    -> cluster EKS, grupo de nodos y AWS Load Balancer Controller
#   imagenes   -> repositorios ECR y construccion/publicacion de las imagenes
#   datos      -> RDS (MySQL, PostgreSQL), ElastiCache (Redis), DynamoDB y SQS
#   aplicacion -> los cinco microservicios de The Store
# ---------------------------------------------------------------------------

locals {
  # nombre del servicio => carpeta del codigo fuente
  services = {
    ui       = "ui"
    catalog  = "catalog"
    carts    = "cart"
    orders   = "orders"
    checkout = "checkout"
  }
}

# --- 1. Red ----------------------------------------------------------------
module "red" {
  source = "./modules/red"

  name            = var.project
  region          = var.region
  cidr            = var.vpc_cidr
  azs             = var.availability_zones
  public_subnets  = var.public_subnets
  private_subnets = var.private_subnets
  db_subnets      = var.db_subnets
}

# --- 2. Cluster de Kubernetes ----------------------------------------------
module "cluster" {
  source = "./modules/cluster"

  name               = var.project
  region             = var.region
  kubernetes_version = var.kubernetes_version
  vpc_id             = module.red.vpc_id
  subnet_ids         = module.red.private_subnet_ids
  service_cidr       = var.service_cidr
  node_instance_type = var.node_instance_type
  node_count         = var.node_count
}

# --- 3. Imagenes de los microservicios -------------------------------------
module "imagenes" {
  source = "./modules/imagenes"

  name        = var.project
  services    = local.services
  source_root = "${path.root}/../the-store/src"
  app_version = var.app_version
}

# --- 4. Bases de datos -----------------------------------------------------
module "datos" {
  source = "./modules/datos"

  name                   = var.project
  vpc_id                 = module.red.vpc_id
  subnet_ids             = module.red.db_subnet_ids
  node_security_group_id = module.cluster.node_security_group_id
  node_role_name         = module.cluster.node_role_name
  db_instance_class      = var.db_instance_class
  cache_node_type        = var.cache_node_type
}

# --- 5. Aplicacion ---------------------------------------------------------
resource "kubernetes_namespace_v1" "this" {
  metadata {
    name = var.namespace
  }

  depends_on = [module.cluster]
}

module "aplicacion" {
  source = "./modules/aplicacion"

  namespace     = kubernetes_namespace_v1.this.metadata[0].name
  region        = var.region
  ingress_cidrs = var.public_subnets
  images        = module.imagenes.images
  replicas      = var.replicas
  ui_theme      = var.ui_theme
  quarantine    = var.quarantine
  databases     = module.datos.connection

  # Las imagenes tienen que estar publicadas y las bases creadas antes de
  # arrancar los microservicios.
  depends_on = [module.imagenes, module.datos]
}
