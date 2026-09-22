output "network_name" {
  description = "Nombre de la red creada."
  value       = docker_network.this.name
}

output "gateway" {
  description = "IP del gateway de la red."
  value       = cidrhost(var.subnet, 1)
}
