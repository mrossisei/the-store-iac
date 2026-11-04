# Objetos Kubernetes de los cinco microservicios en un kind. La configuracion de
# cada servicio esta en locals.tf; las NetworkPolicies, en politicas.tf.
resource "kubernetes_namespace_v1" "this" {
  metadata {
    name   = var.namespace
    labels = { project = "the-store" }
  }
}

resource "kubernetes_secret_v1" "databases" {
  metadata {
    name      = "databases"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
  }

  data = {
    mysql_password    = var.databases.mysql_password
    postgres_password = var.databases.postgres_password
  }

  type = "Opaque"
}

resource "kubernetes_deployment_v1" "service" {
  for_each = local.services

  metadata {
    name      = each.key
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = { app = each.key, tier = each.value.tier }
  }

  spec {
    replicas = lookup(var.replicas, each.key, 2)

    strategy {
      type = "RollingUpdate"
      rolling_update {
        max_surge       = 1
        max_unavailable = 0
      }
    }

    selector {
      match_labels = { app = each.key }
    }

    template {
      metadata {
        labels = { app = each.key, tier = each.value.tier }
      }

      spec {
        automount_service_account_token  = false
        termination_grace_period_seconds = 30

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

          dynamic "env" {
            for_each = each.value.secrets
            content {
              name = env.key
              value_from {
                secret_key_ref {
                  name = kubernetes_secret_v1.databases.metadata[0].name
                  key  = env.value
                }
              }
            }
          }

          startup_probe {
            http_get {
              path = each.value.health
              port = 8080
            }
            period_seconds    = 5
            failure_threshold = 60
          }

          readiness_probe {
            http_get {
              path = each.value.health
              port = 8080
            }
            period_seconds    = 5
            failure_threshold = 30
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
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = { app = each.key, tier = each.value.tier }
  }

  spec {
    type     = each.key == "ui" ? "NodePort" : "ClusterIP"
    selector = { app = each.key }

    port {
      port        = 80
      target_port = 8080
      node_port   = each.key == "ui" ? var.kind.ui_node_port : null
    }
  }
}
