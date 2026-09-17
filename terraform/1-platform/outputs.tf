output "cluster_name" {
  description = "Nombre del clúster kind."
  value       = kind_cluster.this.name
}

output "kubeconfig_path" {
  description = "Ruta del kubeconfig generado (usar: export KUBECONFIG=<ruta>)."
  value       = kind_cluster.this.kubeconfig_path
}

output "kube_context" {
  description = "Contexto de kubeconfig del clúster."
  value       = "kind-${kind_cluster.this.name}"
}

output "cluster_endpoint" {
  description = "Endpoint HTTPS del API server visto desde el host."
  value       = kind_cluster.this.endpoint
}

output "registry_host" {
  description = "Registry visto desde el host (para docker push) y desde los pods (mismo nombre gracias al alias de containerd)."
  value       = "localhost:${var.registry_host_port}"
}

output "registry_internal" {
  description = "Registry visto desde los nodos (red bridge)."
  value       = "${var.registry_name}:5000"
}

output "docker_network" {
  description = "Datos de la red bridge de los nodos."
  value = {
    name    = docker_network.kind.name
    subnet  = var.docker_network_subnet
    gateway = var.docker_network_gateway
  }
}

output "pod_subnet" {
  value = var.pod_subnet
}

output "service_subnet" {
  value = var.service_subnet
}

output "ingress" {
  description = "Puertos del host mapeados al ingress controller y namespace donde corre."
  value = {
    namespace  = helm_release.ingress_nginx.namespace
    http_port  = var.http_host_port
    https_port = var.https_host_port
  }
}
