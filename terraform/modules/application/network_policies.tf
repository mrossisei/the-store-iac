# ---------------------------------------------------------------------------
# Segmentacion de red (equivale a las reglas de un firewall o a los security
# groups de una nube). Se permite solo el trafico necesario:
#
#   Internet --> ui        (unicamente a traves del Ingress Controller)
#   ui       --> backends  (catalog, carts, orders, checkout)
#   backends --> bases de datos
#   cualquier otra cosa    queda bloqueada
# ---------------------------------------------------------------------------

# 1. Por defecto ningun pod acepta conexiones entrantes.
resource "kubernetes_network_policy_v1" "default_deny" {
  metadata {
    name      = "default-deny"
    namespace = var.namespace
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress"]
  }
}

# 2. La UI acepta trafico del Ingress Controller (el unico punto de entrada).
resource "kubernetes_network_policy_v1" "ui_from_ingress" {
  metadata {
    name      = "allow-ui-from-ingress"
    namespace = var.namespace
  }

  spec {
    pod_selector {
      match_labels = { app = "ui" }
    }
    policy_types = ["Ingress"]

    ingress {
      from {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = var.ingress_namespace }
        }
      }
      ports {
        port     = "8080"
        protocol = "TCP"
      }
    }
  }
}

# 3. Los backends aceptan trafico de la UI y entre ellos, no de otros pods.
resource "kubernetes_network_policy_v1" "backends_from_app" {
  metadata {
    name      = "allow-backends-from-app"
    namespace = var.namespace
  }

  spec {
    pod_selector {
      match_labels = { tier = "backend" }
    }
    policy_types = ["Ingress"]

    ingress {
      from {
        pod_selector {
          match_expressions {
            key      = "tier"
            operator = "In"
            values   = ["frontend", "backend"]
          }
        }
      }
      ports {
        port     = "8080"
        protocol = "TCP"
      }
    }
  }
}

# 4. Las bases de datos aceptan trafico solo de los backends.
resource "kubernetes_network_policy_v1" "databases_from_backends" {
  metadata {
    name      = "allow-databases-from-backends"
    namespace = var.namespace
  }

  spec {
    pod_selector {
      match_labels = { tier = "data" }
    }
    policy_types = ["Ingress"]

    ingress {
      from {
        pod_selector {
          match_labels = { tier = "backend" }
        }
      }
    }
  }
}
