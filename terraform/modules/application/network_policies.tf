# ---------------------------------------------------------------------------
# Segmentacion de red (equivale a las reglas de un firewall o a los security
# groups de una nube). Se permite solo el trafico necesario:
#
#   Internet     --> ui              (unicamente a traves del Ingress Controller)
#   ui           --> backends        (catalog, carts, orders, checkout)
#   backends     --> entre si        (checkout llama a orders)
#   cada backend --> su propia base  (catalog -> catalog-db, etc.)
#   cualquier otra cosa queda bloqueada
#
# Las reglas se basan en las etiquetas de los pods: "app" (nombre del servicio)
# y "tier" (frontend, backend o data). Un pod en cuarentena recibe
# tier = "cuarentena" y por lo tanto deja de coincidir con todas las reglas.
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
      match_labels = { app = "ui", tier = "frontend" }
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

# 4. Cada base de datos acepta trafico unicamente del microservicio que la usa.
resource "kubernetes_network_policy_v1" "database_from_owner" {
  for_each = {
    "catalog-db"  = "catalog"
    "orders-db"   = "orders"
    "checkout-db" = "checkout"
  }

  metadata {
    name      = "allow-${each.key}-from-${each.value}"
    namespace = var.namespace
  }

  spec {
    pod_selector {
      match_labels = { app = each.key }
    }
    policy_types = ["Ingress"]

    ingress {
      from {
        pod_selector {
          match_labels = { app = each.value, tier = "backend" }
        }
      }
    }
  }
}

# 5. Cuarentena: un pod con tier = "cuarentena" no puede recibir ni iniciar
#    ninguna conexion (respuesta a un incidente; ver la variable quarantine).
resource "kubernetes_network_policy_v1" "quarantine" {
  metadata {
    name      = "cuarentena"
    namespace = var.namespace
  }

  spec {
    pod_selector {
      match_labels = { tier = "cuarentena" }
    }
    policy_types = ["Ingress", "Egress"]
  }
}
