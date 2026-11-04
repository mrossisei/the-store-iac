mock_provider "kubernetes" {
  mock_data "kubernetes_nodes" {
    defaults = {
      nodes = [{
        metadata = [{ annotations = { "projectcalico.org/IPv4IPIPTunnelAddr" = "10.244.1.0" } }]
        status   = [{ addresses = [{ type = "InternalIP", address = "172.18.0.3" }] }]
      }]
    }
  }
}

variables {
  region    = "us-east-1"
  replicas  = { ui = 2, catalog = 2, carts = 2, orders = 2, checkout = 2 }
  images    = { ui = "r/ui:v1", catalog = "r/catalog:v1", carts = "r/carts:v1", orders = "r/orders:v1", checkout = "r/checkout:v1" }
  kind      = { pod_cidr = "10.244.0.0/16", service_cidr = "172.20.0.0/16", host_ui_port = 8080, ui_node_port = 30080 }
  databases = { mysql_host = "m", mysql_password = "p", postgres_host = "o", postgres_password = "p", redis_host = "r", dynamodb_table = "t", sqs_queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/q" }
}

run "caminos_de_la_pre_entrega" {
  command = plan
  module { source = "./modules/aplicacion" }

  assert {
    condition     = toset(keys(kubernetes_network_policy_v1.flow)) == toset(["ui_catalog", "ui_carts", "ui_checkout", "checkout_orders"])
    error_message = "Solo se permiten los cuatro caminos de la pre-entrega."
  }
}

run "cuarentena_de_checkout" {
  command = plan
  module { source = "./modules/aplicacion" }
  variables { quarantine = ["checkout"] }

  assert {
    condition     = toset(keys(kubernetes_network_policy_v1.flow)) == toset(["ui_catalog", "ui_carts"]) && !contains(keys(kubernetes_network_policy_v1.external_egress), "checkout")
    error_message = "Checkout debe perder todos sus permisos."
  }
  assert {
    condition     = kubernetes_deployment_v1.service["checkout"].spec[0].template[0].metadata[0].labels.app == "checkout"
    error_message = "La cuarentena no toca los pods."
  }
}

run "servicio_inexistente" {
  command = plan
  module { source = "./modules/aplicacion" }
  variables { quarantine = ["typo"] }
  expect_failures = [var.quarantine]
}
