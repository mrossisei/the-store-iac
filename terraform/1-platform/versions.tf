# ---------------------------------------------------------------------------
# Capa 1 - Plataforma
#
# Provisiona la infraestructura "física" del POC: la red Docker (segmento L2
# con su bloque CIDR), el registry de imágenes, el clúster Kubernetes (kind)
# y los add-ons de plataforma (ingress-nginx y metrics-server).
#
# Esta capa tiene su propio estado (terraform.tfstate) porque cambia poco y
# tiene el mayor "radio de explosión": destruirla implica destruir todo.
# ---------------------------------------------------------------------------
terraform {
  required_version = ">= 1.10.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 4.6"
    }
    kind = {
      source  = "tehcyx/kind"
      version = "~> 0.11"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 3.3"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 3.2"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.9"
    }
  }
}
