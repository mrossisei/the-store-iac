# ---------------------------------------------------------------------------
# Cluster de Kubernetes (EKS).
#
# El plano de control lo administra AWS; nosotros declaramos la version, las
# subredes (privadas) donde viven los nodos, el grupo de nodos y los add-ons.
# Se usa el modulo oficial de la comunidad (terraform-aws-modules/eks), que
# resuelve los roles y politicas de IAM y los security groups que EKS exige.
#
# Ademas se instala el Ingress Controller (nginx) con un Service de tipo
# LoadBalancer: AWS crea automaticamente un Network Load Balancer en las
# subredes publicas, que es el unico punto de entrada a la aplicacion.
# ---------------------------------------------------------------------------
terraform {
  required_providers {
    aws        = { source = "hashicorp/aws" }
    helm       = { source = "hashicorp/helm" }
    kubernetes = { source = "hashicorp/kubernetes" }
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
  # operar el cluster desde nuestras maquinas.
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
    }
  }
}

# Ingress Controller: reverse proxy HTTP que enruta cada pedido al Service
# que corresponda. El Service de tipo LoadBalancer hace que AWS cree un NLB.
resource "helm_release" "ingress_nginx" {
  name             = "ingress-nginx"
  namespace        = "ingress-nginx"
  create_namespace = true
  repository       = "https://kubernetes.github.io/ingress-nginx"
  chart            = "ingress-nginx"
  version          = var.ingress_chart_version
  wait             = true
  timeout          = 600

  values = [yamlencode({
    controller = {
      service = {
        type = "LoadBalancer"
        annotations = {
          "service.beta.kubernetes.io/aws-load-balancer-type"                              = "nlb"
          "service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled" = "true"
        }
      }
    }
  })]

  depends_on = [module.eks]
}

# Nombre DNS del balanceador que AWS asigno al Ingress Controller.
data "kubernetes_service_v1" "ingress" {
  metadata {
    name      = "ingress-nginx-controller"
    namespace = helm_release.ingress_nginx.namespace
  }

  depends_on = [helm_release.ingress_nginx]
}
