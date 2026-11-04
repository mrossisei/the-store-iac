output "active_services" {
  description = "Servicios fuera de cuarentena."
  value       = local.active
}

output "allowed_flows" {
  description = "Caminos permitidos entre servicios activos."
  value       = local.allowed_flows
}

output "policy_names" {
  description = "Nombres de todas las NetworkPolicies creadas."
  value = concat(
    [kubernetes_network_policy_v1.default_deny.metadata[0].name],
    [for p in kubernetes_network_policy_v1.flow : p.metadata[0].name],
    [for p in kubernetes_network_policy_v1.flow_egress : p.metadata[0].name],
    [for p in kubernetes_network_policy_v1.external_egress : p.metadata[0].name],
    [for p in kubernetes_network_policy_v1.ui_ingress : p.metadata[0].name]
  )
}

output "ui_node_source_cidrs" {
  description = "IPs /32 de nodo admitidas como origen de la UI."
  value       = toset([for ip in local.node_source_ips : "${ip}/32"])
}
