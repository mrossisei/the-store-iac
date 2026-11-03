mock_provider "kubernetes" {}
run "kind_app_contract" {
  command = apply
  module { source = "../modules/aplicacion" }
  variables {
    namespace = "the-store-test"
    region    = "us-east-1"
    images    = { ui = "registry/ui@sha256:abc", catalog = "registry/catalog@sha256:abc", carts = "registry/carts@sha256:abc", orders = "registry/orders@sha256:abc", checkout = "registry/checkout@sha256:abc" }
    databases = { mysql_host = "mysql.private", mysql_password = "private-mysql", postgres_host = "postgres.private", postgres_password = "private-postgres", redis_host = "redis.private", dynamodb_table = "shared-carts", sqs_queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/shared-orders" }
  }
  assert {
    condition     = length(kubernetes_deployment_v1.service) == 5 && alltrue([for d in kubernetes_deployment_v1.service : tonumber(d.spec[0].replicas) == 2 && d.spec[0].strategy[0].rolling_update[0].max_unavailable == "0" && d.spec[0].template[0].spec[0].container[0].image_pull_policy == "IfNotPresent"])
    error_message = "Cinco servicios, diez pods por kind y rollout sin interrupción deliberada."
  }
  assert {
    condition     = kubernetes_service_v1.service["ui"].spec[0].type == "NodePort" && kubernetes_service_v1.service["ui"].spec[0].port[0].node_port == 30080 && alltrue([for s, d in kubernetes_service_v1.service : d.spec[0].port[0].target_port == "8080" && (s == "ui" || d.spec[0].type == "ClusterIP")])
    error_message = "UI NodePort30080 y backends ClusterIP, todos TCP8080."
  }
  assert {
    condition     = alltrue([for s, d in kubernetes_deployment_v1.service : !contains([for e in d.spec[0].template[0].spec[0].container[0].env : e.name], "AWS_ACCESS_KEY_ID") && alltrue([for e in d.spec[0].template[0].spec[0].container[0].env : endswith(e.name, "PASSWORD") ? length(e.value_from) == 1 : true])]) && issensitive(kubernetes_secret_v1.databases.data)
    error_message = "Sin credenciales AWS estáticas; passwords SQL en Secret refs."
  }
}
run "quarantine_keeps_pod_templates" {
  command = plan
  module { source = "../modules/aplicacion" }
  variables {
    quarantine = ["checkout"]
    namespace  = "the-store-test"
    region     = "us-east-1"
    images     = { ui = "registry/ui@sha256:abc", catalog = "registry/catalog@sha256:abc", carts = "registry/carts@sha256:abc", orders = "registry/orders@sha256:abc", checkout = "registry/checkout@sha256:abc" }
    databases  = { mysql_host = "mysql.private", mysql_password = "private-mysql", postgres_host = "postgres.private", postgres_password = "private-postgres", redis_host = "redis.private", dynamodb_table = "shared-carts", sqs_queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/shared-orders" }
  }

  assert {
    condition     = kubernetes_deployment_v1.service["checkout"].spec[0].template[0].metadata[0].labels.tier == "backend" && kubernetes_deployment_v1.service["checkout"].spec[0].template[0].metadata[0].labels.app == "checkout"
    error_message = "Cuarentena no cambia PodTemplate ni etiquetas."
  }
}
