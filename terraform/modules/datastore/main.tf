# ---------------------------------------------------------------------------
# Módulo reutilizable "datastore": un servicio con estado (base de datos,
# cache, broker) desplegado como StatefulSet de una réplica con volumen
# persistente, Secret con credenciales y Service ClusterIP.
#
# Es el equivalente local de un servicio administrado (RDS, ElastiCache,
# Amazon MQ, DynamoDB): la aplicación sólo conoce host, puerto y credenciales.
# ---------------------------------------------------------------------------
locals {
  selector_labels = {
    "app.kubernetes.io/name"      = var.name
    "app.kubernetes.io/instance"  = var.name
    "app.kubernetes.io/component" = "datastore"
    "app.kubernetes.io/owner"     = "the-store"
  }

  common_labels = merge(var.labels, local.selector_labels, {
    "app.kubernetes.io/managed-by" = "terraform"
  })
}

resource "kubernetes_secret_v1" "this" {
  metadata {
    name      = var.name
    namespace = var.namespace
    labels    = local.common_labels
  }

  data = var.secret_env
  type = "Opaque"
}

resource "kubernetes_service_v1" "this" {
  metadata {
    name      = var.name
    namespace = var.namespace
    labels    = local.common_labels
  }

  spec {
    type     = "ClusterIP"
    selector = local.selector_labels

    port {
      name        = "main"
      port        = var.port
      target_port = var.port
      protocol    = "TCP"
    }

    dynamic "port" {
      for_each = var.extra_ports
      content {
        name        = port.key
        port        = port.value
        target_port = port.value
        protocol    = "TCP"
      }
    }
  }
}

resource "kubernetes_stateful_set_v1" "this" {
  metadata {
    name      = var.name
    namespace = var.namespace
    labels    = local.common_labels
  }

  spec {
    service_name = kubernetes_service_v1.this.metadata[0].name
    replicas     = 1

    selector {
      match_labels = local.selector_labels
    }

    template {
      metadata {
        labels = local.common_labels
      }

      spec {
        dynamic "security_context" {
          for_each = var.fs_group != null ? [1] : []
          content {
            fs_group = var.fs_group
          }
        }

        container {
          name              = var.name
          image             = var.image
          image_pull_policy = "IfNotPresent"
          args              = var.args

          port {
            name           = "main"
            container_port = var.port
          }

          dynamic "port" {
            for_each = var.extra_ports
            content {
              name           = port.key
              container_port = port.value
            }
          }

          dynamic "env" {
            for_each = var.env
            content {
              name  = env.key
              value = env.value
            }
          }

          env_from {
            secret_ref {
              name = kubernetes_secret_v1.this.metadata[0].name
            }
          }

          readiness_probe {
            dynamic "exec" {
              for_each = var.readiness_command != null ? [1] : []
              content {
                command = var.readiness_command
              }
            }
            dynamic "tcp_socket" {
              for_each = var.readiness_command == null ? [1] : []
              content {
                port = var.port
              }
            }
            initial_delay_seconds = 5
            period_seconds        = 5
            failure_threshold     = 12
          }

          resources {
            requests = {
              cpu    = var.resources.cpu_request
              memory = var.resources.memory_request
            }
            limits = {
              memory = var.resources.memory_limit
            }
          }

          dynamic "security_context" {
            for_each = var.run_as_user != null ? [1] : []
            content {
              run_as_user = var.run_as_user
            }
          }

          volume_mount {
            name       = "data"
            mount_path = var.data_path
          }
        }
      }
    }

    volume_claim_template {
      metadata {
        name   = "data"
        labels = local.common_labels
      }
      spec {
        access_modes       = ["ReadWriteOnce"]
        storage_class_name = var.storage_class
        resources {
          requests = {
            storage = var.storage_size
          }
        }
      }
    }
  }

  wait_for_rollout = true

  timeouts {
    create = "10m"
    update = "10m"
  }
}
