# ---------------------------------------------------------------------------
# Los cinco microservicios de The Store.
#
# Cada uno se despliega como un Deployment (que mantiene N copias del proceso)
# y se publica con un Service (nombre DNS interno + IP virtual que reparte el
# trafico entre las copias). La UI ademas se publica hacia afuera con un
# Ingress, y cuatro NetworkPolicies controlan quien puede hablar con quien.
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
        JAVA_OPTS                        = local.java_opts
        RETAIL_CART_PERSISTENCE_PROVIDER = "in-memory"
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
        RETAIL_ORDERS_MESSAGING_PROVIDER   = "in-memory"
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
    replicas = lookup(var.replicas, each.key, 1)

    selector {
      match_labels = { app = each.key }
    }

    template {
      metadata {
        labels = { app = each.key, tier = each.value.tier }
      }

      spec {
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

# Punto de entrada desde afuera: todo el trafico HTTP del host va a la UI.
resource "kubernetes_ingress_v1" "ui" {
  metadata {
    name      = "the-store"
    namespace = var.namespace
  }

  spec {
    ingress_class_name = "nginx"

    rule {
      host = var.hostname
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
