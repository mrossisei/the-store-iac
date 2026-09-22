output "url" {
  description = "Dirección web de la tienda."
  value       = "http://${var.hostname}"
}

output "kubeconfig" {
  description = "Archivo de credenciales del cluster (export KUBECONFIG=...)."
  value       = module.cluster.kubeconfig_path
}

output "nodes" {
  description = "Nodos del cluster y bloque de red en el que viven."
  value = {
    cantidad = var.worker_count + 1
    red      = var.docker_subnet
  }
}

output "networks" {
  description = "Bloques de direcciones usados por el cluster."
  value = {
    nodos     = var.docker_subnet
    pods      = var.pod_subnet
    servicios = var.service_subnet
  }
}

output "images" {
  description = "Imágenes desplegadas."
  value       = local.images
}
