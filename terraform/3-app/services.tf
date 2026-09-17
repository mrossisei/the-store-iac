# ---------------------------------------------------------------------------
# Microservicios. Todos usan el mismo módulo; lo que cambia es la
# configuración (imagen, variables, réplicas, dependencias).
# ---------------------------------------------------------------------------
module "catalog" {
  source = "../modules/microservice"

  name      = "catalog"
  namespace = kubernetes_namespace_v1.this.metadata[0].name
  image     = local.images.catalog
  replicas  = local.replicas.catalog

  env = merge(
    { RETAIL_CATALOG_PERSISTENCE_PROVIDER = var.persistence ? "mysql" : "in-memory" },
    var.persistence ? {
      RETAIL_CATALOG_PERSISTENCE_ENDPOINT = module.catalog_db[0].endpoint
      RETAIL_CATALOG_PERSISTENCE_DB_NAME  = "catalogdb"
      RETAIL_CATALOG_PERSISTENCE_USER     = "catalog"
    } : {},
  )
  secret_env = var.persistence ? {
    RETAIL_CATALOG_PERSISTENCE_PASSWORD = { secret_name = module.catalog_db[0].secret_name, key = "MARIADB_PASSWORD" }
  } : {}

  depends_on_services = var.persistence ? [module.catalog_db[0].endpoint] : []
  readiness_path      = "/health"
  resources           = { cpu_request = "256m", memory_request = "256Mi", memory_limit = "256Mi" }
  labels              = local.app_labels
}

module "carts" {
  source = "../modules/microservice"

  name      = "carts"
  namespace = kubernetes_namespace_v1.this.metadata[0].name
  image     = local.images.carts
  replicas  = local.replicas.carts

  env = merge(
    {
      JAVA_OPTS                        = local.java_opts
      RETAIL_CART_PERSISTENCE_PROVIDER = var.persistence ? "dynamodb" : "in-memory"
    },
    var.persistence ? {
      RETAIL_CART_PERSISTENCE_DYNAMODB_ENDPOINT     = "http://${module.carts_db[0].endpoint}"
      RETAIL_CART_PERSISTENCE_DYNAMODB_TABLE_NAME   = "Items"
      RETAIL_CART_PERSISTENCE_DYNAMODB_CREATE_TABLE = "true"
      # DynamoDB Local no valida credenciales, pero el SDK exige que existan.
      AWS_ACCESS_KEY_ID     = "local"
      AWS_SECRET_ACCESS_KEY = "local"
      AWS_REGION            = "us-west-2"
    } : {},
  )

  depends_on_services     = var.persistence ? [module.carts_db[0].endpoint] : []
  readiness_path          = "/actuator/health/readiness"
  readiness_initial_delay = 15
  resources               = { cpu_request = "256m", memory_request = "512Mi", memory_limit = "512Mi" }
  labels                  = local.app_labels
}

module "orders" {
  source = "../modules/microservice"

  name      = "orders"
  namespace = kubernetes_namespace_v1.this.metadata[0].name
  image     = local.images.orders
  replicas  = local.replicas.orders

  env = merge(
    {
      JAVA_OPTS                          = local.java_opts
      RETAIL_ORDERS_PERSISTENCE_PROVIDER = var.persistence ? "postgres" : "in-memory"
      RETAIL_ORDERS_MESSAGING_PROVIDER   = var.persistence ? "rabbitmq" : "in-memory"
    },
    var.persistence ? {
      RETAIL_ORDERS_PERSISTENCE_ENDPOINT         = module.orders_db[0].endpoint
      RETAIL_ORDERS_PERSISTENCE_NAME             = "orders"
      RETAIL_ORDERS_PERSISTENCE_USERNAME         = "orders"
      RETAIL_ORDERS_MESSAGING_RABBITMQ_ADDRESSES = module.orders_mq[0].endpoint
      RETAIL_ORDERS_MESSAGING_RABBITMQ_USERNAME  = "orders"
    } : {},
  )
  secret_env = var.persistence ? {
    RETAIL_ORDERS_PERSISTENCE_PASSWORD        = { secret_name = module.orders_db[0].secret_name, key = "POSTGRES_PASSWORD" }
    RETAIL_ORDERS_MESSAGING_RABBITMQ_PASSWORD = { secret_name = module.orders_mq[0].secret_name, key = "RABBITMQ_DEFAULT_PASS" }
  } : {}

  depends_on_services     = var.persistence ? [module.orders_db[0].endpoint, module.orders_mq[0].endpoint] : []
  readiness_path          = "/actuator/health/readiness"
  readiness_initial_delay = 15
  resources               = { cpu_request = "256m", memory_request = "512Mi", memory_limit = "512Mi" }
  labels                  = local.app_labels
}

module "checkout" {
  source = "../modules/microservice"

  name      = "checkout"
  namespace = kubernetes_namespace_v1.this.metadata[0].name
  image     = local.images.checkout
  replicas  = local.replicas.checkout

  env = merge(
    {
      RETAIL_CHECKOUT_PERSISTENCE_PROVIDER = var.persistence ? "redis" : "in-memory"
      RETAIL_CHECKOUT_ENDPOINTS_ORDERS     = module.orders.url
    },
    var.persistence ? {
      RETAIL_CHECKOUT_PERSISTENCE_REDIS_URL = "redis://${module.checkout_redis[0].endpoint}"
    } : {},
  )

  depends_on_services = concat(
    [module.orders.service_host],
    var.persistence ? [module.checkout_redis[0].endpoint] : [],
  )
  readiness_path = "/health"
  resources      = { cpu_request = "128m", memory_request = "256Mi", memory_limit = "256Mi" }
  labels         = local.app_labels
}

module "ui" {
  source = "../modules/microservice"

  name      = "ui"
  namespace = kubernetes_namespace_v1.this.metadata[0].name
  image     = local.images.ui
  replicas  = local.replicas.ui

  env = {
    JAVA_OPTS                    = local.java_opts
    RETAIL_UI_THEME              = var.ui_theme
    RETAIL_UI_ENDPOINTS_CATALOG  = module.catalog.url
    RETAIL_UI_ENDPOINTS_CARTS    = module.carts.url
    RETAIL_UI_ENDPOINTS_ORDERS   = module.orders.url
    RETAIL_UI_ENDPOINTS_CHECKOUT = module.checkout.url
  }
  env_from_field = {
    METADATA_KUBERNETES_POD_NAME  = "metadata.name"
    METADATA_KUBERNETES_NAMESPACE = "metadata.namespace"
    METADATA_KUBERNETES_NODE_NAME = "spec.nodeName"
  }

  add_capabilities        = ["NET_BIND_SERVICE"]
  readiness_path          = "/actuator/health/readiness"
  readiness_initial_delay = 15
  resources               = { cpu_request = "128m", memory_request = "512Mi", memory_limit = "512Mi" }
  autoscaling             = var.autoscaling_ui
  labels                  = local.app_labels
}
