# ---------------------------------------------------------------------------
# Cluster de Kubernetes.
#
# Se crea con kind (Kubernetes IN Docker): cada nodo del cluster es un
# contenedor de Docker conectado a la red del modulo networking. Equivale a un
# cluster administrado (EKS/GKE) con su grupo de nodos.
#
# Ademas se instala el Ingress Controller, que es el punto de entrada HTTP del
# cluster (equivale a un balanceador de carga de capa 7).
# ---------------------------------------------------------------------------

terraform {
  required_providers {
    kind = { source = "tehcyx/kind" }
    helm = { source = "hashicorp/helm" }
  }
}

resource "kind_cluster" "this" {
  name            = var.cluster_name
  node_image      = var.node_image
  wait_for_ready  = true
  kubeconfig_path = pathexpand("~/.kube/${var.cluster_name}.kubeconfig")

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    # Bloques de direcciones internos del cluster.
    networking {
      pod_subnet     = var.pod_subnet
      service_subnet = var.service_subnet
    }

    # Nodo de control. Es tambien el nodo de borde: publica los puertos 80 y
    # 443 de la maquina y sobre el corre el Ingress Controller.
    node {
      role   = "control-plane"
      labels = { "ingress-ready" = "true" }

      extra_port_mappings {
        container_port = 80
        host_port      = 80
      }
      extra_port_mappings {
        container_port = 443
        host_port      = 443
      }
    }

    # Nodos worker: ejecutan los microservicios y las bases de datos.
    dynamic "node" {
      for_each = range(var.worker_count)
      content {
        role = "worker"
      }
    }
  }
}

# Ingress Controller (nginx). Escucha en los puertos 80/443 del nodo de borde
# y enruta cada pedido HTTP al Service que corresponda segun el nombre de host.
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
      hostPort     = { enabled = true }
      service      = { type = "ClusterIP" }
      nodeSelector = { "ingress-ready" = "true" }
      tolerations = [{
        key      = "node-role.kubernetes.io/control-plane"
        operator = "Exists"
        effect   = "NoSchedule"
      }]
    }
  })]

  depends_on = [kind_cluster.this]
}
