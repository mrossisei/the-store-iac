# ---------------------------------------------------------------------------
# Módulo reutilizable "microservice": empaqueta el patrón que repiten los
# cinco servicios de The Store (ServiceAccount + ConfigMap + Deployment +
# Service + HPA/PDB opcionales) con los mismos hardening que trae el manifiesto
# original (dist/kubernetes.yaml): usuario no root, root filesystem de sólo
# lectura, sin capabilities, /tmp en memoria.
# ---------------------------------------------------------------------------
locals {
  selector_labels = {
    "app.kubernetes.io/name"      = var.name
    "app.kubernetes.io/instance"  = var.name
    "app.kubernetes.io/component" = "service"
    "app.kubernetes.io/owner"     = "the-store"
  }

  common_labels = merge(var.labels, local.selector_labels, {
    "app.kubernetes.io/managed-by" = "terraform"
  })

  hpa_enabled = var.autoscaling != null
}

resource "kubernetes_service_account_v1" "this" {
  metadata {
    name      = var.name
    namespace = var.namespace
    labels    = local.common_labels
  }
}

resource "kubernetes_config_map_v1" "this" {
  metadata {
    name      = var.name
    namespace = var.namespace
    labels    = local.common_labels
  }

  data = var.env
}

resource "kubernetes_deployment_v1" "this" {
  metadata {
    name      = var.name
    namespace = var.namespace
    labels    = local.common_labels
  }

  spec {
    # Con HPA el número de réplicas lo decide el autoscaler: no lo fijamos
    # (el atributo es "computed": Terraform no lo gestiona ni detecta drift).
    # Sin HPA lo fijamos, y un `kubectl scale` manual aparece como drift.
    replicas = var.autoscaling != null ? null : tostring(var.replicas)

    strategy {
      type = "RollingUpdate"
      rolling_update {
        max_unavailable = "1"
        max_surge       = "1"
      }
    }

    selector {
      match_labels = local.selector_labels
    }

    template {
      metadata {
        labels = local.common_labels
        annotations = {
          # Fuerza un rollout cuando cambia la configuración (el ConfigMap
          # solo no reinicia pods).
          "the-store.itba/config-hash" = sha1(jsonencode(var.env))
        }
      }

      spec {
        service_account_name = kubernetes_service_account_v1.this.metadata[0].name

        security_context {
          fs_group        = 1000
          run_as_non_root = true
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }

        # Espera (TCP) a los servicios de los que depende, para que el
        # readiness no falle en cascada durante el arranque del entorno.
        dynamic "init_container" {
          for_each = length(var.depends_on_services) > 0 ? [1] : []
          content {
            name  = "wait-for-dependencies"
            image = "busybox:1.37"
            command = ["sh", "-c", join(" && ", [
              for h in var.depends_on_services :
              "until nc -z -w 2 ${split(":", h)[0]} ${length(split(":", h)) > 1 ? split(":", h)[1] : "80"}; do echo waiting for ${h}; sleep 2; done"
            ])]
            security_context {
              run_as_non_root            = true
              run_as_user                = 1000
              allow_privilege_escalation = false
              read_only_root_filesystem  = true
              capabilities {
                drop = ["ALL"]
              }
            }
          }
        }

        container {
          name              = var.name
          image             = var.image
          image_pull_policy = "IfNotPresent"

          port {
            name           = "http"
            container_port = var.container_port
            protocol       = "TCP"
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map_v1.this.metadata[0].name
            }
          }

          dynamic "env" {
            for_each = var.env_from_field
            content {
              name = env.key
              value_from {
                field_ref {
                  field_path = env.value
                }
              }
            }
          }

          dynamic "env" {
            for_each = var.secret_env
            content {
              name = env.key
              value_from {
                secret_key_ref {
                  name = env.value.secret_name
                  key  = env.value.key
                }
              }
            }
          }

          readiness_probe {
            http_get {
              path = var.readiness_path
              port = var.container_port
            }
            initial_delay_seconds = var.readiness_initial_delay
            period_seconds        = 5
            failure_threshold     = 6
          }

          liveness_probe {
            http_get {
              path = var.readiness_path
              port = var.container_port
            }
            initial_delay_seconds = 60
            period_seconds        = 15
            failure_threshold     = 3
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

          security_context {
            run_as_non_root            = true
            run_as_user                = 1000
            read_only_root_filesystem  = true
            allow_privilege_escalation = false
            capabilities {
              drop = ["ALL"]
              add  = var.add_capabilities
            }
          }

          volume_mount {
            name       = "tmp"
            mount_path = "/tmp"
          }
        }

        volume {
          name = "tmp"
          empty_dir {
            medium = "Memory"
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
      name        = "http"
      port        = var.service_port
      target_port = "http"
      protocol    = "TCP"
    }
  }
}

resource "kubernetes_horizontal_pod_autoscaler_v2" "this" {
  count = local.hpa_enabled ? 1 : 0

  metadata {
    name      = var.name
    namespace = var.namespace
    labels    = local.common_labels
  }

  spec {
    min_replicas = var.autoscaling.min_replicas
    max_replicas = var.autoscaling.max_replicas

    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = kubernetes_deployment_v1.this.metadata[0].name
    }

    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = var.autoscaling.target_cpu_percent
        }
      }
    }

    behavior {
      scale_down {
        stabilization_window_seconds = 60
        select_policy                = "Max"
        policy {
          type           = "Pods"
          value          = 1
          period_seconds = 30
        }
      }
      scale_up {
        stabilization_window_seconds = 0
        select_policy                = "Max"
        policy {
          type           = "Pods"
          value          = 2
          period_seconds = 15
        }
      }
    }
  }
}

# Con más de una réplica, garantizamos que siempre quede al menos una
# disponible durante drenados de nodo o actualizaciones.
resource "kubernetes_pod_disruption_budget_v1" "this" {
  count = var.replicas > 1 || local.hpa_enabled ? 1 : 0

  metadata {
    name      = var.name
    namespace = var.namespace
    labels    = local.common_labels
  }

  spec {
    min_available = 1
    selector {
      match_labels = local.selector_labels
    }
  }
}
