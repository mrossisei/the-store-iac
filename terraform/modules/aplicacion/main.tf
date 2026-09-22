# ---------------------------------------------------------------------------
# Los cinco microservicios de The Store.
#
# Cada uno se despliega como un Deployment (que mantiene N copias del proceso)
# y se publica con un Service (nombre DNS interno + IP virtual que reparte el
# trafico entre las copias). La UI ademas se publica hacia afuera con un
# Ingress, que el AWS Load Balancer Controller convierte en un Application
# Load Balancer, y las NetworkPolicies controlan quien puede hablar con quien.
# ---------------------------------------------------------------------------
terraform {
  required_providers {
    kubernetes = { source = "hashicorp/kubernetes" }
  }
}

locals {
  java_opts = "-XX:MaxRAMPercentage=75.0"

  # Tabla con la configuracion de cada microservicio.
  services = {
    ui = {
      tier   = "frontend"
      health = "/actuator/health/readiness"
      memory = "512Mi"
      env = {
        JAVA_OPTS                    = local.java_opts
        RETAIL_UI_THEME              = var.ui_theme
        RETAIL_UI_ENDPOINTS_CATALOG  = "http://catalog"
        RETAIL_UI_ENDPOINTS_CARTS    = "http://carts"
        RETAIL_UI_ENDPOINTS_ORDERS   = "http://orders"
        RETAIL_UI_ENDPOINTS_CHECKOUT = "http://checkout"
      }
    }

    catalog = {
      tier   = "backend"
      health = "/health"
      memory = "256Mi"
      env = {
        RETAIL_CATALOG_PERSISTENCE_PROVIDER = "mysql"
        RETAIL_CATALOG_PERSISTENCE_ENDPOINT = "${var.databases.mysql_host}:3306"
        RETAIL_CATALOG_PERSISTENCE_DB_NAME  = "catalogdb"
        RETAIL_CATALOG_PERSISTENCE_USER     = "catalog"
        RETAIL_CATALOG_PERSISTENCE_PASSWORD = var.databases.mysql_password
      }
    }

    carts = {
      tier   = "backend"
      health = "/actuator/health/readiness"
      memory = "512Mi"
      env = {
        JAVA_OPTS                                     = local.java_opts
        RETAIL_CART_PERSISTENCE_PROVIDER              = "dynamodb"
        RETAIL_CART_PERSISTENCE_DYNAMODB_TABLE_NAME   = var.databases.dynamodb_table
        RETAIL_CART_PERSISTENCE_DYNAMODB_CREATE_TABLE = "false"
        AWS_REGION                                    = var.region
      }
    }

    orders = {
      tier   = "backend"
      health = "/actuator/health/readiness"
      memory = "512Mi"
      env = {
        JAVA_OPTS                          = local.java_opts
        RETAIL_ORDERS_PERSISTENCE_PROVIDER = "postgres"
        RETAIL_ORDERS_PERSISTENCE_ENDPOINT = "${var.databases.postgres_host}:5432"
        RETAIL_ORDERS_PERSISTENCE_NAME     = "orders"
        RETAIL_ORDERS_PERSISTENCE_USERNAME = "orders"
        RETAIL_ORDERS_PERSISTENCE_PASSWORD = var.databases.postgres_password
        RETAIL_ORDERS_MESSAGING_PROVIDER   = "sqs"
        RETAIL_ORDERS_MESSAGING_SQS_TOPIC  = var.databases.sqs_queue_url
        AWS_REGION                         = var.region
      }
    }

    checkout = {
      tier   = "backend"
      health = "/health"
      memory = "256Mi"
      env = {
        RETAIL_CHECKOUT_PERSISTENCE_PROVIDER  = "redis"
        RETAIL_CHECKOUT_PERSISTENCE_REDIS_URL = "redis://${var.databases.redis_host}:6379"
        RETAIL_CHECKOUT_ENDPOINTS_ORDERS      = "http://orders"
      }
    }
  }
}

resource "kubernetes_deployment_v1" "service" {
  for_each = local.services

  metadata {
    name      = each.key
    namespace = var.namespace
    labels    = { app = each.key, tier = each.value.tier }
  }

  spec {
    replicas = lookup(var.replicas, each.key, 2)

    selector {
      match_labels = { app = each.key }
    }

    template {
      metadata {
        # Un servicio en cuarentena cambia de capa: las reglas de red dejan
        # de permitirle cualquier comunicacion.
        labels = {
          app  = each.key
          tier = contains(var.quarantine, each.key) ? "cuarentena" : each.value.tier
        }
      }

      spec {
        # Reparte las replicas entre las zonas de disponibilidad.
        topology_spread_constraint {
          max_skew           = 1
          topology_key       = "topology.kubernetes.io/zone"
          when_unsatisfiable = "ScheduleAnyway"
          label_selector {
            match_labels = { app = each.key }
          }
        }

        container {
          name              = each.key
          image             = var.images[each.key]
          image_pull_policy = "IfNotPresent"

          port {
            container_port = 8080
          }

          dynamic "env" {
            for_each = each.value.env
            content {
              name  = env.key
              value = env.value
            }
          }

          readiness_probe {
            http_get {
              path = each.value.health
              port = 8080
            }
            initial_delay_seconds = 15
            period_seconds        = 5
            failure_threshold     = 30
          }

          resources {
            requests = { cpu = "100m", memory = each.value.memory }
            limits   = { memory = each.value.memory }
          }
        }

        # Reparte las replicas de un mismo servicio entre las zonas de
        # disponibilidad (y por lo tanto entre los nodos). Con una sola
        # replica no cambia nada.
        topology_spread_constraint {
          max_skew           = 1
          topology_key       = "topology.kubernetes.io/zone"
          when_unsatisfiable = "ScheduleAnyway"
          label_selector {
            match_labels = { app = each.key }
          }
        }
      }
    }
  }
}

# Nombre DNS interno de cada microservicio (ej: http://catalog).
resource "kubernetes_service_v1" "service" {
  for_each = local.services

  metadata {
    name      = each.key
    namespace = var.namespace
    labels    = { app = each.key, tier = each.value.tier }
  }

  spec {
    type     = "ClusterIP"
    selector = { app = each.key }

    port {
      port        = 80
      target_port = 8080
    }
  }
}

# Punto de entrada desde afuera: el AWS Load Balancer Controller crea un ALB
# publico y manda todo el trafico HTTP directamente a los pods de la UI (no se
# fija un nombre de host porque no hay un dominio propio).
resource "kubernetes_ingress_v1" "ui" {
  metadata {
    name      = "the-store"
    namespace = var.namespace
    annotations = {
      "alb.ingress.kubernetes.io/scheme"           = "internet-facing"
      "alb.ingress.kubernetes.io/target-type"      = "ip"
      "alb.ingress.kubernetes.io/healthcheck-path" = "/actuator/health/readiness"
    }
  }

  # Espera a que el controlador cree el ALB y publique su nombre DNS.
  wait_for_load_balancer = true

  spec {
    ingress_class_name = "alb"

    rule {
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = kubernetes_service_v1.service["ui"].metadata[0].name
              port { number = 80 }
            }
          }
        }
      }
    }
  }
}
