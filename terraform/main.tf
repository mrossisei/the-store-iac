# ---------------------------------------------------------------------------
# The Store - Infraestructura como Código con Terraform
# TP Especial de Redes de Información - ITBA
#
# Este archivo orquesta los cuatro módulos de la solución:
#   networking  -> red donde viven los nodos del cluster
#   cluster     -> cluster de Kubernetes + Ingress Controller
#   databases   -> bases de datos de los microservicios
#   application -> los cinco microservicios de The Store
# ---------------------------------------------------------------------------

# --- 1. Red ----------------------------------------------------------------
module "networking" {
  source = "./modules/networking"

  # El nombre "kind" no es casual: ver el comentario del modulo.
  network_name = "kind"
  subnet       = var.docker_subnet
}

# --- 2. Cluster de Kubernetes ----------------------------------------------
module "cluster" {
  source = "./modules/cluster"

  cluster_name   = var.cluster_name
  network_name   = module.networking.network_name
  worker_count   = var.worker_count
  pod_subnet     = var.pod_subnet
  service_subnet = var.service_subnet
}

# --- 3. Imágenes de los microservicios -------------------------------------
# Se construyen desde el código fuente de la aplicación y se cargan en los
# nodos del cluster (equivale a `docker build` + `kind load docker-image`).
locals {
  # nombre del servicio => carpeta del código fuente
  services = {
    ui       = "ui"
    catalog  = "catalog"
    carts    = "cart"
    orders   = "orders"
    checkout = "checkout"
  }

  images = { for name, dir in local.services : name => "the-store-${name}:${var.app_version}" }
}

resource "docker_image" "service" {
  for_each = local.services

  name = local.images[each.key]

  build {
    context = "${path.root}/../the-store/src/${each.value}"
  }
}

resource "null_resource" "load_image" {
  for_each = local.services

  triggers = {
    image_id = docker_image.service[each.key].image_id
    cluster  = module.cluster.cluster_name
  }

  provisioner "local-exec" {
    command = "kind load docker-image ${local.images[each.key]} --name ${module.cluster.cluster_name}"
  }
}

# --- 4. Namespace ----------------------------------------------------------
resource "kubernetes_namespace_v1" "this" {
  metadata {
    name = var.namespace
  }

  depends_on = [module.cluster]
}

# --- 5. Bases de datos -----------------------------------------------------
module "databases" {
  source = "./modules/databases"

  namespace = kubernetes_namespace_v1.this.metadata[0].name
}

# --- 6. Aplicación --------------------------------------------------------
module "application" {
  source = "./modules/application"

  namespace  = kubernetes_namespace_v1.this.metadata[0].name
  images     = local.images
  replicas   = var.replicas
  hostname   = var.hostname
  ui_theme   = var.ui_theme
  quarantine = var.quarantine
  databases  = module.databases.connection

  # Las imagenes tienen que estar en los nodos y las bases levantadas antes
  # de arrancar los microservicios.
  depends_on = [null_resource.load_image, module.databases]
}
