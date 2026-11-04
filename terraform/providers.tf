terraform {
  required_version = ">= 1.10"

  required_providers {
    aws        = { source = "hashicorp/aws", version = "= 6.66.0" }
    docker     = { source = "kreuzwerker/docker", version = "~> 4.6" }
    external   = { source = "hashicorp/external", version = "= 2.4.2" }
    kubernetes = { source = "hashicorp/kubernetes", version = "= 3.4.0" }
    random     = { source = "hashicorp/random", version = "= 3.9.1" }
  }

  # El bucket se indica en terraform init con -backend-config.
  backend "s3" {
    key          = "the-store/kind/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = { Project = var.project, ManagedBy = "terraform" }
  }
}

# Token temporal para publicar las imágenes en ECR.
data "aws_ecr_authorization_token" "this" {}

provider "docker" {
  registry_auth {
    address  = data.aws_ecr_authorization_token.this.proxy_endpoint
    username = data.aws_ecr_authorization_token.this.user_name
    password = data.aws_ecr_authorization_token.this.password
  }
}

# Un provider por clúster. Sus kubeconfigs salen del script de acceso, que corre
# cuando las EC2 ya existen.
provider "kubernetes" {
  alias       = "kind_a"
  config_path = data.external.acceso.result.kubeconfig_a
}

provider "kubernetes" {
  alias       = "kind_b"
  config_path = data.external.acceso.result.kubeconfig_b
}
