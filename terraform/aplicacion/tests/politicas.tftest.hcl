# Aislado de T08: python3 scripts/probar-politicas-terraform.py
mock_provider "kubernetes" {
  mock_data "kubernetes_nodes" {
    defaults = {
      nodes = [{
        metadata = [{ annotations = { "projectcalico.org/IPv4IPIPTunnelAddr" = "10.244.1.0" } }]
        status   = [{ addresses = [{ type = "InternalIP", address = "172.24.0.3" }] }]
      }]
    }
  }
}

run "baseline" {
  command = plan
  module { source = "../modules/aplicacion/modules/politicas" }
  assert {
    condition     = length(output.allowed_flows) == 4 && length(output.active_services) == 5
    error_message = "Baseline debe permitir exactamente cuatro aristas y cinco servicios activos."
  }
  assert {
    condition     = toset(kubernetes_network_policy_v1.default_deny.spec[0].policy_types) == toset(["Ingress", "Egress"])
    error_message = "El aislamiento por defecto debe cubrir entrada y salida."
  }
  assert {
    condition     = alltrue([for p in kubernetes_network_policy_v1.external_egress : toset(p.spec[0].egress[0].to[0].ip_block[0].except) == toset(["10.244.0.0/16", "172.20.0.0/16"])])
    error_message = "El allow externo nunca puede incluir pods ni Services."
  }
  assert {
    condition     = output.ui_node_source_cidrs == toset(["172.24.0.3/32", "10.244.1.0/32"])
    error_message = "UI debe contemplar InternalIP y túnel Calico /32, sin permitir todo podCIDR."
  }
  assert {
    condition     = length(kubernetes_network_policy_v1.flow) == 4 && length(kubernetes_network_policy_v1.flow_egress) == 4
    error_message = "Cada arista necesita permiso específico en ambos extremos."
  }
}

run "checkout_quarantine" {
  command = plan
  module { source = "../modules/aplicacion/modules/politicas" }
  variables { quarantine = ["checkout"] }
  assert {
    condition     = toset(keys(output.allowed_flows)) == toset(["ui_catalog", "ui_carts"])
    error_message = "Cuarentena debe retirar UI→Checkout y Checkout→Orders."
  }
  assert {
    condition     = !contains(keys(kubernetes_network_policy_v1.external_egress), "checkout") && length(kubernetes_network_policy_v1.external_egress) == 4
    error_message = "Checkout tampoco puede conservar DNS/Redis/Internet por allow alternativo."
  }
  assert {
    condition     = alltrue([for p in kubernetes_network_policy_v1.flow : p.spec[0].pod_selector[0].match_labels.app != "checkout" && p.spec[0].ingress[0].from[0].pod_selector[0].match_labels.app != "checkout"])
    error_message = "Ningún allow entrante puede seleccionar checkout en cualquiera de sus extremos."
  }
}

run "all_quarantined" {
  command = plan
  module { source = "../modules/aplicacion/modules/politicas" }
  variables { quarantine = ["ui", "catalog", "carts", "checkout", "orders"] }
  assert {
    condition     = length(output.policy_names) == 1 && output.policy_names[0] == "default-deny"
    error_message = "Solo debe quedar el deny cuando todos están en cuarentena."
  }
}

run "invalid_quarantine" {
  command = plan
  module { source = "../modules/aplicacion/modules/politicas" }
  variables { quarantine = ["typo"] }
  expect_failures = [var.quarantine]
}
