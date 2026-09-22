# ---------------------------------------------------------------------------
# Providers: plugins que Terraform usa para hablar con cada plataforma.
#   docker     -> daemon de Docker local (red e imágenes)
#   kind       -> crea el cluster de Kubernetes (Kubernetes IN Docker)
#   kubernetes -> objetos dentro del cluster (Deployments, Services, etc.)
#   helm       -> instala el Ingress Controller (paquete de Kubernetes)
# ---------------------------------------------------------------------------
terraform {
  required_version = ">= 1.10"

  required_providers {
    docker     = { source = "kreuzwerker/docker", version = "~> 4.6" }
    kind       = { source = "tehcyx/kind", version = "~> 0.11" }
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 3.2" }
    helm       = { source = "hashicorp/helm", version = "~> 3.3" }
    random     = { source = "hashicorp/random", version = "~> 3.9" }
    null       = { source = "hashicorp/null", version = "~> 3.3" }
  }
}

# El estado se guarda en un archivo local (terraform.tfstate). Para trabajar en
# equipo se lo puede mover a un backend remoto con bloqueo, por ejemplo:
#
#   terraform {
#     backend "s3" {
#       bucket       = "tp-redes-terraform-state"
#       key          = "the-store/terraform.tfstate"
#       region       = "us-east-1"
#       use_lockfile = true
#     }
#   }

provider "docker" {}

provider "kind" {}

# Los providers de Kubernetes y Helm se autentican con las credenciales que
# devuelve el cluster recién creado por el módulo cluster.
provider "kubernetes" {
  host                   = module.cluster.endpoint
  client_certificate     = module.cluster.client_certificate
  client_key             = module.cluster.client_key
  cluster_ca_certificate = module.cluster.cluster_ca_certificate
}

provider "helm" {
  kubernetes = {
    host                   = module.cluster.endpoint
    client_certificate     = module.cluster.client_certificate
    client_key             = module.cluster.client_key
    cluster_ca_certificate = module.cluster.cluster_ca_certificate
  }
}
