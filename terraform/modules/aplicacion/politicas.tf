# Default deny y los caminos de la pre-entrega. Cuarentena retira los permisos de
# un servicio sin tocar sus pods.
data "kubernetes_nodes" "cluster" {}

locals {
  active = setsubtract(toset(["ui", "catalog", "carts", "orders", "checkout"]), var.quarantine)
  flows = {
    ui_catalog      = { source = "ui", destination = "catalog" }
    ui_carts        = { source = "ui", destination = "carts" }
    ui_checkout     = { source = "ui", destination = "checkout" }
    checkout_orders = { source = "checkout", destination = "orders" }
  }
  allowed_flows = { for key, flow in local.flows : key => flow
    if contains(local.active, flow.source) && contains(local.active, flow.destination)
  }
  cluster_cidrs = [var.kind.pod_cidr, var.kind.service_cidr]
  # Calico IPIP/VXLAN puede usar una IP /32 dentro del pool como origen SNAT.
  # Se descubren IPs del nodo; nunca se permite su podCIDR completo.
  node_source_ips = toset(concat(
    flatten([for node in data.kubernetes_nodes.cluster.nodes : [
      for address in node.status[0].addresses : address.address
      if address.type == "InternalIP" && can(cidrnetmask("${address.address}/32"))
    ]]),
    compact(flatten([for node in data.kubernetes_nodes.cluster.nodes : [
      for key in ["projectcalico.org/IPv4IPIPTunnelAddr", "projectcalico.org/IPv4VXLANTunnelAddr"] :
      lookup(node.metadata[0].annotations, key, "")
    ]]))
  ))
}

# Policies son aditivas. No hay allow global por tier ni un allow DNS/externo
# que seleccione endpoints en cuarentena. Este deny sigue seleccionándolos.
resource "kubernetes_network_policy_v1" "default_deny" {
  metadata {
    name      = "default-deny"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
  }
  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}

resource "kubernetes_network_policy_v1" "flow" {
  for_each = local.allowed_flows
  metadata {
    name      = "allow-${replace(each.key, "_", "-")}"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
  }
  spec {
    pod_selector { match_labels = { app = each.value.destination } }
    policy_types = ["Ingress"]
    ingress {
      from {
        pod_selector { match_labels = { app = each.value.source } }
      }
      ports {
        port     = "8080"
        protocol = "TCP"
      }
    }
  }
}

resource "kubernetes_network_policy_v1" "flow_egress" {
  for_each = local.allowed_flows
  metadata {
    name      = "allow-${replace(each.key, "_", "-")}-egress"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
  }
  spec {
    pod_selector { match_labels = { app = each.value.source } }
    policy_types = ["Egress"]
    egress {
      to {
        pod_selector { match_labels = { app = each.value.destination } }
      }
      ports {
        port     = "8080"
        protocol = "TCP"
      }
    }
  }
}

# Cada allow externo pertenece a un servicio activo. Excluir ambas redes
# impide que 0/0 sea una ruta alternativa hacia pods/Services de cuarentena.
# Datos AWS, IMDSv2 e Internet permanecen sujetos a SG/rutas del host.
resource "kubernetes_network_policy_v1" "external_egress" {
  for_each = local.active
  metadata {
    name      = "allow-${each.key}-external"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
  }
  spec {
    pod_selector { match_labels = { app = each.key } }
    policy_types = ["Egress"]
    egress {
      to {
        ip_block {
          cidr   = "0.0.0.0/0"
          except = local.cluster_cidrs
        }
      }
    }
    egress {
      to {
        namespace_selector { match_labels = { "kubernetes.io/metadata.name" = "kube-system" } }
        pod_selector { match_labels = { "k8s-app" = "kube-dns" } }
      }
      ports {
        port     = "53"
        protocol = "UDP"
      }
      ports {
        port     = "53"
        protocol = "TCP"
      }
    }
  }
}

# NodePort externalTrafficPolicy=Cluster puede presentar la IP del nodo
# después de SNAT, no la subred ALB. El SG exterior limita ALB→EC2:8080.
# El tráfico directo desde pods no obtiene permiso por esta regla.
resource "kubernetes_network_policy_v1" "ui_ingress" {
  count = contains(local.active, "ui") ? 1 : 0
  metadata {
    name      = "allow-ui-nodeport"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
  }
  spec {
    pod_selector { match_labels = { app = "ui" } }
    policy_types = ["Ingress"]
    ingress {
      from {
        ip_block {
          cidr   = "0.0.0.0/0"
          except = local.cluster_cidrs
        }
      }
      dynamic "from" {
        for_each = local.node_source_ips
        content {
          ip_block { cidr = "${from.value}/32" }
        }
      }
      ports {
        port     = "8080"
        protocol = "TCP"
      }
    }
  }
}
