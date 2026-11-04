variable "name" {
  description = "Prefijo de los recursos de red."
  type        = string
}

variable "region" {
  description = "Región, para los nombres de los VPC Endpoints."
  type        = string
}

variable "cidr" {
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

variable "application_port" {
  description = "Puerto de las EC2 que recibe el tráfico del ALB."
  type        = number
}
