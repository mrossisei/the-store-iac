output "name" {
  value = module.eks.cluster_name
}

output "endpoint" {
  value = module.eks.cluster_endpoint
}

output "certificate_authority" {
  value = module.eks.cluster_certificate_authority_data
}

output "node_security_group_id" {
  description = "Security group de los nodos (y de sus pods)."
  value       = module.eks.node_security_group_id
}

output "node_role_name" {
  description = "Rol de IAM de los nodos, que heredan los pods."
  value       = module.eks.node_iam_role_name
}

output "ingress_namespace" {
  value = helm_release.ingress_nginx.namespace
}

output "load_balancer_hostname" {
  description = "Nombre DNS del NLB creado para el Ingress Controller."
  value       = try(data.kubernetes_service_v1.ingress.status[0].load_balancer[0].ingress[0].hostname, "pendiente")
}
