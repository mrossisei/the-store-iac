# ---------------------------------------------------------------------------
# Capa de datos (sólo si var.persistence = true). Un datastore por servicio,
# como en la arquitectura de referencia de The Store:
#   catalog  -> MariaDB (MySQL)     orders -> PostgreSQL + RabbitMQ
#   checkout -> Redis               carts  -> DynamoDB Local
# Las credenciales se generan con random_password y viven en Secrets.
# ---------------------------------------------------------------------------
resource "random_password" "catalog_db" {
  count   = var.persistence ? 1 : 0
  length  = 24
  special = false
}

resource "random_password" "catalog_db_root" {
  count   = var.persistence ? 1 : 0
  length  = 24
  special = false
}

resource "random_password" "orders_db" {
  count   = var.persistence ? 1 : 0
  length  = 24
  special = false
}

resource "random_password" "orders_mq" {
  count   = var.persistence ? 1 : 0
  length  = 24
  special = false
}

module "catalog_db" {
  source = "../modules/datastore"
  count  = var.persistence ? 1 : 0

  name      = "catalog-db"
  namespace = kubernetes_namespace_v1.this.metadata[0].name
  image     = "mariadb:11.4"
  port      = local.ports.mariadb
  data_path = "/var/lib/mysql"

  env = {
    MARIADB_DATABASE = "catalogdb"
    MARIADB_USER     = "catalog"
  }
  secret_env = {
    MARIADB_PASSWORD      = random_password.catalog_db[0].result
    MARIADB_ROOT_PASSWORD = random_password.catalog_db_root[0].result
  }

  readiness_command = ["healthcheck.sh", "--connect", "--innodb_initialized"]
  storage_size      = var.storage_size
  fs_group          = 999
  labels            = local.data_labels
}

module "orders_db" {
  source = "../modules/datastore"
  count  = var.persistence ? 1 : 0

  name      = "orders-db"
  namespace = kubernetes_namespace_v1.this.metadata[0].name
  image     = "postgres:17-alpine"
  port      = local.ports.postgres
  data_path = "/var/lib/postgresql/data"

  env = {
    POSTGRES_DB   = "orders"
    POSTGRES_USER = "orders"
    PGDATA        = "/var/lib/postgresql/data/pgdata"
  }
  secret_env = {
    POSTGRES_PASSWORD = random_password.orders_db[0].result
  }

  readiness_command = ["pg_isready", "-U", "orders", "-d", "orders"]
  storage_size      = var.storage_size
  fs_group          = 70
  labels            = local.data_labels
}

module "orders_mq" {
  source = "../modules/datastore"
  count  = var.persistence ? 1 : 0

  name        = "orders-mq"
  namespace   = kubernetes_namespace_v1.this.metadata[0].name
  image       = "rabbitmq:4-management-alpine"
  port        = local.ports.amqp
  extra_ports = { management = 15672 }
  data_path   = "/var/lib/rabbitmq"

  env = {
    RABBITMQ_DEFAULT_USER = "orders"
  }
  secret_env = {
    RABBITMQ_DEFAULT_PASS = random_password.orders_mq[0].result
  }

  readiness_command = ["rabbitmq-diagnostics", "-q", "ping"]
  storage_size      = var.storage_size
  fs_group          = 999
  labels            = local.data_labels
  resources = {
    cpu_request    = "100m"
    memory_request = "256Mi"
    memory_limit   = "768Mi"
  }
}

module "checkout_redis" {
  source = "../modules/datastore"
  count  = var.persistence ? 1 : 0

  name      = "checkout-redis"
  namespace = kubernetes_namespace_v1.this.metadata[0].name
  image     = "redis:7-alpine"
  port      = local.ports.redis
  data_path = "/data"
  args      = ["redis-server", "--appendonly", "yes"]

  readiness_command = ["redis-cli", "ping"]
  storage_size      = var.storage_size
  fs_group          = 999
  labels            = local.data_labels
  resources = {
    cpu_request    = "50m"
    memory_request = "64Mi"
    memory_limit   = "256Mi"
  }
}

module "carts_db" {
  source = "../modules/datastore"
  count  = var.persistence ? 1 : 0

  name      = "carts-db"
  namespace = kubernetes_namespace_v1.this.metadata[0].name
  image     = "amazon/dynamodb-local:latest"
  port      = local.ports.dynamodb
  data_path = "/home/dynamodblocal/data"
  args      = ["-jar", "DynamoDBLocal.jar", "-sharedDb", "-dbPath", "/home/dynamodblocal/data"]

  storage_size = var.storage_size
  run_as_user  = 1000
  fs_group     = 1000
  labels       = local.data_labels
}
