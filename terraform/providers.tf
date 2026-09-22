# ---------------------------------------------------------------------------
# Providers: plugins con los que Terraform habla con cada plataforma.
#   aws        -> todos los recursos de AWS (red, EKS, RDS, ElastiCache, ...)
#   kubernetes -> objetos dentro del cluster (Deployments, Services, ...)
#   helm       -> instala el AWS Load Balancer Controller (paquete de Kubernetes)
#   docker     -> construye las imagenes en la maquina y las publica en ECR
#   random     -> contrasenas de las bases de datos
# ---------------------------------------------------------------------------
terraform {
  required_version = ">= 1.10"

  required_providers {
    aws        = { source = "hashicorp/aws", version = "~> 6.0" }
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 3.2" }
    helm       = { source = "hashicorp/helm", version = "~> 3.3" }
    docker     = { source = "kreuzwerker/docker", version = "~> 4.6" }
    random     = { source = "hashicorp/random", version = "~> 3.9" }
  }
}

provider "aws" {
  region = var.region

  # Todos los recursos llevan estas etiquetas: permite ver el costo del TP
  # en la consola de facturacion y borrar todo lo que quede huerfano.
  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
    }
  }
}

# Los providers de Kubernetes y Helm se autentican contra el API server de EKS
# con un token que genera la CLI de AWS a partir de las mismas credenciales.
provider "kubernetes" {
  host                   = module.cluster.endpoint
  cluster_ca_certificate = base64decode(module.cluster.certificate_authority)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.cluster.name, "--region", var.region]
  }
}

provider "helm" {
  kubernetes = {
    host                   = module.cluster.endpoint
    cluster_ca_certificate = base64decode(module.cluster.certificate_authority)

    exec = {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.cluster.name, "--region", var.region]
    }
  }
}

# Token temporal (12 horas) para publicar imagenes en el registry ECR de la cuenta.
data "aws_ecr_authorization_token" "this" {}

provider "docker" {
  registry_auth {
    address  = data.aws_ecr_authorization_token.this.proxy_endpoint
    username = data.aws_ecr_authorization_token.this.user_name
    password = data.aws_ecr_authorization_token.this.password
  }
}
