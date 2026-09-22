# ---------------------------------------------------------------------------
# Segmentacion de red dentro del cluster (equivale a las reglas de un firewall).
# Se permite solo el trafico necesario:
#
#   Internet --> ui        (unicamente a traves del ALB)
#   ui       --> backends  (catalog, carts, orders, checkout)
#   backends --> entre si  (checkout llama a orders)
#   cualquier otra cosa queda bloqueada
#
# Las bases de datos estan fuera del cluster: su acceso lo controla el security
# group de la capa de datos (modulo datos), que solo acepta conexiones
# desde los nodos.
#
# Las reglas se basan en las etiquetas de los pods: "app" (nombre del servicio)
# y "tier" (frontend o backend). Un pod en cuarentena recibe tier = "cuarentena"
# y por lo tanto deja de coincidir con todas las reglas de permiso.
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

# 2. La UI acepta trafico del ALB (el unico punto de entrada), cuyas
#    interfaces viven en las subredes publicas.
resource "kubernetes_network_policy_v1" "ui_from_ingress" {
  metadata {
    name      = "allow-ui-from-alb"
    namespace = var.namespace
  }

  spec {
    pod_selector {
      match_labels = { app = "ui", tier = "frontend" }
    }
    policy_types = ["Ingress"]

    ingress {
      dynamic "from" {
        for_each = var.ingress_cidrs
        content {
          ip_block {
            cidr = from.value
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

# 4. Cuarentena: un pod con tier = "cuarentena" no puede recibir ni iniciar
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
