# ---------------------------------------------------------------------------
# Cluster de Kubernetes (EKS).
#
# El plano de control lo administra AWS; nosotros declaramos la version, las
# subredes (privadas) donde viven los nodos, el grupo de nodos y los add-ons.
# Se usa el modulo oficial de la comunidad (terraform-aws-modules/eks), que
# resuelve los roles y politicas de IAM y los security groups que EKS exige.
#
# Ademas se instala el AWS Load Balancer Controller: a partir del Ingress de
# la aplicacion crea un Application Load Balancer en las subredes publicas,
# que es el unico punto de entrada, y enruta los pedidos HTTP directamente a
# los pods de la UI.
# ---------------------------------------------------------------------------
terraform {
  required_providers {
    aws  = { source = "hashicorp/aws" }
    helm = { source = "hashicorp/helm" }
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.25"

  name               = var.name
  kubernetes_version = var.kubernetes_version
  vpc_id             = var.vpc_id
  subnet_ids         = var.subnet_ids
  service_ipv4_cidr  = var.service_cidr

  # El API server se alcanza desde Internet (autenticado con IAM) para poder
  # operar el cluster desde nuestras maquinas; los nodos usan el endpoint
  # privado.
  endpoint_public_access = true

  # La identidad de AWS que crea el cluster queda como administradora.
  enable_cluster_creator_admin_permissions = true

  addons = {
    coredns    = {}
    kube-proxy = {}
    vpc-cni = {
      before_compute = true
      # Habilita la aplicacion de NetworkPolicies en el plugin de red de AWS.
      configuration_values = jsonencode({ enableNetworkPolicy = "true" })
    }
  }

  eks_managed_node_groups = {
    workers = {
      instance_types = [var.node_instance_type]
      # Tamano fijo: cambiar node_count escala el grupo hacia arriba o abajo.
      min_size     = var.node_count
      desired_size = var.node_count
      max_size     = var.node_count

      # Los pods usan las credenciales del rol del nodo (DynamoDB, SQS), que
      # se obtienen del servicio de metadatos de la instancia; con el limite
      # por defecto de un salto no lo alcanzan.
      metadata_options = { http_put_response_hop_limit = 2 }
    }
  }
}

# --- AWS Load Balancer Controller ------------------------------------------
# Rol de IAM que el controlador asume a traves de su service account (IRSA):
# necesita crear y administrar el ALB, sus target groups y security groups.
module "lb_controller_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts"
  version = "~> 6.8"

  name                                   = "${var.name}-aws-load-balancer-controller"
  attach_load_balancer_controller_policy = true

  oidc_providers = {
    eks = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }
}

resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  namespace  = "kube-system"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = var.lb_controller_chart_version
  wait       = true
  timeout    = 600

  values = [yamlencode({
    clusterName = module.eks.cluster_name
    region      = var.region
    vpcId       = var.vpc_id
    serviceAccount = {
      create      = true
      name        = "aws-load-balancer-controller"
      annotations = { "eks.amazonaws.com/role-arn" = module.lb_controller_role.arn }
    }
  })]

  depends_on = [module.eks, module.lb_controller_role]
}
