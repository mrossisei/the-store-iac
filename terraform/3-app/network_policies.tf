# ---------------------------------------------------------------------------
# Segmentación de red como código (NetworkPolicies).
#
# Modelo "zero trust" dentro del namespace: se deniega todo el tráfico de
# entrada y salida, y se habilitan explícitamente sólo los flujos que la
# aplicación necesita. La tabla `flows` es, en la práctica, la lista de
# reglas de firewall (ACL) del entorno.
# ---------------------------------------------------------------------------
locals {
  app_flows = [
    { from = "ui", to = "catalog", port = 8080 },
    { from = "ui", to = "carts", port = 8080 },
    { from = "ui", to = "orders", port = 8080 },
    { from = "ui", to = "checkout", port = 8080 },
    { from = "checkout", to = "orders", port = 8080 },
  ]

  data_flows = var.persistence ? [
    { from = "catalog", to = "catalog-db", port = local.ports.mariadb },
    { from = "orders", to = "orders-db", port = local.ports.postgres },
    { from = "orders", to = "orders-mq", port = local.ports.amqp },
    { from = "checkout", to = "checkout-redis", port = local.ports.redis },
    { from = "carts", to = "carts-db", port = local.ports.dynamodb },
  ] : []

  flows = concat(local.app_flows, local.data_flows)

  workloads = var.enable_network_policies ? distinct(concat(
    [for f in local.flows : f.from],
    [for f in local.flows : f.to],
  )) : []
}

# 1) Denegar todo (ingress + egress) para todos los pods del namespace.
resource "kubernetes_network_policy_v1" "default_deny" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "default-deny-all"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = local.common_labels
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}

# 2) Todos los pods pueden resolver nombres contra CoreDNS (kube-system).
resource "kubernetes_network_policy_v1" "allow_dns" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-dns-egress"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = local.common_labels
  }

  spec {
    pod_selector {}
    policy_types = ["Egress"]

    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "kube-system" }
        }
        pod_selector {
          match_labels = { "k8s-app" = "kube-dns" }
        }
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

# 3) El ingress controller (namespace ingress-nginx, la "DMZ") puede llegar a la UI.
resource "kubernetes_network_policy_v1" "allow_ingress_to_ui" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-ingress-controller-to-ui"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = local.common_labels
  }

  spec {
    pod_selector {
      match_labels = { "app.kubernetes.io/name" = "ui" }
    }
    policy_types = ["Ingress"]

    ingress {
      from {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = data.terraform_remote_state.platform.outputs.ingress.namespace }
        }
      }
      ports {
        port     = "8080"
        protocol = "TCP"
      }
    }
  }
}

# 4) Una política por workload con sus flujos permitidos (entrada y salida).
resource "kubernetes_network_policy_v1" "workload" {
  for_each = toset(local.workloads)

  metadata {
    name      = "allow-${each.key}"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = local.common_labels
  }

  spec {
    pod_selector {
      match_labels = { "app.kubernetes.io/name" = each.key }
    }
    policy_types = ["Ingress", "Egress"]

    dynamic "ingress" {
      for_each = [for f in local.flows : f if f.to == each.key]
      content {
        from {
          pod_selector {
            match_labels = { "app.kubernetes.io/name" = ingress.value.from }
          }
        }
        ports {
          port     = tostring(ingress.value.port)
          protocol = "TCP"
        }
      }
    }

    dynamic "egress" {
      for_each = [for f in local.flows : f if f.from == each.key]
      content {
        to {
          pod_selector {
            match_labels = { "app.kubernetes.io/name" = egress.value.to }
          }
        }
        ports {
          port     = tostring(egress.value.port)
          protocol = "TCP"
        }
      }
    }
  }

  # Nota: estas políticas NO dependen de los Deployments a propósito. Si se
  # crearan después de ellos, la denegación por defecto (que sí se aplica
  # enseguida) bloquearía los initContainers y los readiness de los servicios
  # y el apply quedaría trabado (deadlock). Las políticas sólo referencian
  # labels, por lo que pueden existir antes que los pods.
}
