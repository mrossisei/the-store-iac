# ---------------------------------------------------------------------------
# Bases de datos de los microservicios.
#
# Cada servicio que necesita persistir datos tiene su propia base, igual que en
# la arquitectura original de The Store. Se despliegan como StatefulSet (un
# tipo de objeto de Kubernetes pensado para aplicaciones con estado) con un
# disco persistente propio. Equivalen a los servicios administrados de una
# nube: RDS para MySQL/PostgreSQL y ElastiCache para Redis.
# ---------------------------------------------------------------------------

terraform {
  required_providers {
    kubernetes = { source = "hashicorp/kubernetes" }
    random     = { source = "hashicorp/random" }
  }
}


# Contrasenas generadas por Terraform: no hay credenciales escritas en el codigo.
resource "random_password" "mysql" {
  length  = 20
  special = false
}

resource "random_password" "postgres" {
  length  = 20
  special = false
}

locals {
  databases = {
    # Base del catalogo de productos
    "catalog-db" = {
      image     = "mariadb:11.4"
      port      = 3306
      data_path = "/var/lib/mysql"
      fs_group  = 999
      args      = null
      probe     = ["healthcheck.sh", "--connect", "--innodb_initialized"]
      env = {
        MARIADB_DATABASE      = "catalogdb"
        MARIADB_USER          = "catalog"
        MARIADB_PASSWORD      = random_password.mysql.result
        MARIADB_ROOT_PASSWORD = random_password.mysql.result
      }
    }

    # Base de las ordenes de compra
    "orders-db" = {
      image     = "postgres:17-alpine"
      port      = 5432
      data_path = "/var/lib/postgresql/data"
      fs_group  = 70
      args      = null
      probe     = ["pg_isready", "-U", "orders", "-d", "orders"]
      env = {
        POSTGRES_DB       = "orders"
        POSTGRES_USER     = "orders"
        POSTGRES_PASSWORD = random_password.postgres.result
        PGDATA            = "/var/lib/postgresql/data/pgdata"
      }
    }

    # Cache del proceso de compra
    "checkout-db" = {
      image     = "redis:7-alpine"
      port      = 6379
      data_path = "/data"
      fs_group  = 999
      args      = ["redis-server", "--appendonly", "yes"]
      probe     = ["redis-cli", "ping"]
      env       = {}
    }
  }
}

resource "kubernetes_stateful_set_v1" "db" {
  for_each = local.databases

  metadata {
    name      = each.key
    namespace = var.namespace
    labels    = { app = each.key, tier = "data" }
  }

  spec {
    service_name = each.key
    replicas     = 1

    selector {
      match_labels = { app = each.key }
    }

    template {
      metadata {
        labels = { app = each.key, tier = "data" }
      }

      spec {
        security_context {
          fs_group = each.value.fs_group
        }

        container {
          name  = each.key
          image = each.value.image
          args  = each.value.args

          port {
            container_port = each.value.port
          }

          dynamic "env" {
            for_each = each.value.env
            content {
              name  = env.key
              value = env.value
            }
          }

          readiness_probe {
            exec {
              command = each.value.probe
            }
            initial_delay_seconds = 5
            period_seconds        = 5
            failure_threshold     = 30
          }

          resources {
            requests = { cpu = "100m", memory = "256Mi" }
            limits   = { memory = "512Mi" }
          }

          volume_mount {
            name       = "data"
            mount_path = each.value.data_path
          }
        }
      }
    }

    # Disco persistente: los datos sobreviven al reinicio del pod.
    volume_claim_template {
      metadata {
        name = "data"
      }
      spec {
        access_modes = ["ReadWriteOnce"]
        resources {
          requests = { storage = var.storage_size }
        }
      }
    }
  }
}

# Cada base se publica con un nombre DNS interno (ej: orders-db) que los
# microservicios usan para conectarse.
resource "kubernetes_service_v1" "db" {
  for_each = local.databases

  metadata {
    name      = each.key
    namespace = var.namespace
    labels    = { app = each.key, tier = "data" }
  }

  spec {
    type     = "ClusterIP"
    selector = { app = each.key }

    port {
      port        = each.value.port
      target_port = each.value.port
    }
  }
}
