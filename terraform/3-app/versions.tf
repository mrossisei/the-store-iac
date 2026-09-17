# ---------------------------------------------------------------------------
# Capa 3 - Aplicación (un workspace de Terraform por entorno: dev, prod)
#
# Despliega The Store en un namespace propio del entorno: capa de datos
# (opcional), los cinco microservicios, el Ingress (con TLS opcional) y las
# NetworkPolicies (segmentación de red como código).
#
# Uso:
#   terraform workspace select -or-create prod
#   terraform apply -var-file=../environments/prod.tfvars
# ---------------------------------------------------------------------------
terraform {
  required_version = ">= 1.10.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 3.2"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.9"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}
