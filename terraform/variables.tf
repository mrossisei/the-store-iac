variable "project" {
  description = "Prefijo de todos los recursos."
  type        = string
}

variable "region" {
  description = "Región de AWS."
  type        = string
}

variable "vpc_cidr" {
  description = "Bloque CIDR de la VPC."
  type        = string
}

variable "zones" {
  description = "Zonas de disponibilidad y sus subredes."
  type = map(object({
    availability_zone = string
    public_cidr       = string
    private_cidr      = string
    db_cidr           = string
  }))
}

variable "services" {
  description = "Microservicios: nombre => carpeta del código fuente."
  type        = map(string)
}

variable "image_versions" {
  description = "Versiones a construir y publicar en ECR."
  type        = set(string)
}

variable "ami_id" {
  description = "AMI de las EC2 (Amazon Linux 2023, x86_64)."
  type        = string
}

variable "instance_type" {
  description = "Tipo de las EC2; Academy admite hasta large."
  type        = string
}

variable "instance_profile_name" {
  description = "Perfil de instancia existente, que contiene LabRole."
  type        = string
}

variable "kind" {
  description = "Redes y puertos de los clústeres kind."
  type = object({
    pod_cidr     = string
    service_cidr = string
    host_ui_port = number
    ui_node_port = number
  })
}

variable "db_instance_class" {
  description = "Tipo de las instancias RDS."
  type        = string
}

variable "cache_node_type" {
  description = "Tipo de nodo de ElastiCache."
  type        = string
}

# --- Casos de uso ----------------------------------------------------------
variable "app_version" {
  description = "Versión publicada en ECR a desplegar."
  type        = string

  validation {
    condition     = contains(var.image_versions, var.app_version)
    error_message = "app_version debe ser una de image_versions."
  }
}

variable "replicas" {
  description = "Réplicas de cada microservicio."
  type        = map(number)
}

variable "quarantine" {
  description = "Microservicios aislados por NetworkPolicies."
  type        = set(string)
  default     = []
}
