locals {
  java_opts = "-XX:MaxRAMPercentage=75.0"

  # Tabla con la configuracion de cada microservicio. secrets asocia variables
  # de entorno con claves del Secret databases.
  services = {
    ui = {
      tier    = "frontend"
      health  = "/actuator/health/readiness"
      memory  = "512Mi"
      secrets = {}
      env = {
        JAVA_OPTS                         = local.java_opts
        RETAIL_UI_THEME                   = var.ui_theme
        RETAIL_UI_ENDPOINTS_CATALOG       = "http://catalog"
        RETAIL_UI_ENDPOINTS_CARTS         = "http://carts"
        RETAIL_UI_ENDPOINTS_ORDERS        = "http://orders"
        RETAIL_UI_ENDPOINTS_CHECKOUT      = "http://checkout"
        SERVER_TOMCAT_ACCESSLOG_ENABLED   = "true"
        SERVER_TOMCAT_BASEDIR             = "/tmp/tomcat"
        SERVER_TOMCAT_ACCESSLOG_DIRECTORY = "logs"
        SERVER_TOMCAT_ACCESSLOG_PATTERN   = "%a %s %U"
      }
    }

    catalog = {
      tier    = "backend"
      health  = "/health"
      memory  = "256Mi"
      secrets = { RETAIL_CATALOG_PERSISTENCE_PASSWORD = "mysql_password" }
      env = {
        RETAIL_CATALOG_PERSISTENCE_PROVIDER = "mysql"
        RETAIL_CATALOG_PERSISTENCE_ENDPOINT = "${nonsensitive(var.databases.mysql_host)}:3306"
        RETAIL_CATALOG_PERSISTENCE_DB_NAME  = "catalogdb"
        RETAIL_CATALOG_PERSISTENCE_USER     = "catalog"
      }
    }

    carts = {
      tier    = "backend"
      health  = "/actuator/health/readiness"
      memory  = "512Mi"
      secrets = {}
      env = {
        JAVA_OPTS                                     = local.java_opts
        RETAIL_CART_PERSISTENCE_PROVIDER              = "dynamodb"
        RETAIL_CART_PERSISTENCE_DYNAMODB_TABLE_NAME   = nonsensitive(var.databases.dynamodb_table)
        RETAIL_CART_PERSISTENCE_DYNAMODB_CREATE_TABLE = "false"
        AWS_REGION                                    = var.region
      }
    }

    orders = {
      tier    = "backend"
      health  = "/actuator/health/readiness"
      memory  = "512Mi"
      secrets = { RETAIL_ORDERS_PERSISTENCE_PASSWORD = "postgres_password" }
      env = {
        JAVA_OPTS                          = local.java_opts
        RETAIL_ORDERS_PERSISTENCE_PROVIDER = "postgres"
        RETAIL_ORDERS_PERSISTENCE_ENDPOINT = "${nonsensitive(var.databases.postgres_host)}:5432"
        RETAIL_ORDERS_PERSISTENCE_NAME     = "orders"
        RETAIL_ORDERS_PERSISTENCE_USERNAME = "orders"
        RETAIL_ORDERS_MESSAGING_PROVIDER   = "sqs"
        RETAIL_ORDERS_MESSAGING_SQS_TOPIC  = nonsensitive(var.databases.sqs_queue_url)
        AWS_REGION                         = var.region
      }
    }

    checkout = {
      tier    = "backend"
      health  = "/health"
      memory  = "256Mi"
      secrets = {}
      env = {
        RETAIL_CHECKOUT_PERSISTENCE_PROVIDER  = "redis"
        RETAIL_CHECKOUT_PERSISTENCE_REDIS_URL = "redis://${nonsensitive(var.databases.redis_host)}:6379"
        RETAIL_CHECKOUT_ENDPOINTS_ORDERS      = "http://orders"
      }
    }
  }
}
