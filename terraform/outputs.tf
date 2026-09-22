output "url" {
  description = "Direccion web de la tienda (nombre DNS del balanceador)."
  value       = "http://${module.aplicacion.load_balancer_hostname}"
}

output "kubeconfig_command" {
  description = "Comando para configurar kubectl contra el cluster."
  value       = "aws eks update-kubeconfig --name ${module.cluster.name} --region ${var.region}"
}

output "networks" {
  description = "Bloques de direcciones usados."
  value = {
    vpc             = var.vpc_cidr
    public_subnets  = var.public_subnets
    private_subnets = var.private_subnets
    db_subnets      = var.db_subnets
    services        = var.service_cidr
  }
}

output "images" {
  description = "Imagenes desplegadas (repositorios ECR)."
  value       = module.imagenes.images
}

output "databases" {
  description = "Endpoints de la capa de datos."
  value       = module.datos.endpoints
}
