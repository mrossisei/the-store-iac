variable "name" {
  description = "Prefijo de los recursos de red."
  type        = string
}

variable "region" {
  description = "Region (para los nombres de los VPC Endpoints)."
  type        = string
}

variable "cidr" {
  description = "Bloque CIDR de la VPC."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.cidr))
    error_message = "Se requiere un CIDR IPv4 valido."
  }
}

variable "azs" {
  description = "Zonas de disponibilidad."
  type        = list(string)
}

variable "public_subnets" {
  description = "Bloques de las subredes publicas, una por zona."
  type        = list(string)

  validation {
    condition     = length(var.public_subnets) == length(var.azs)
    error_message = "Se requiere una subred publica por zona."
  }
}

variable "private_subnets" {
  description = "Bloques de las subredes privadas, una por zona."
  type        = list(string)

  validation {
    condition     = length(var.private_subnets) == length(var.azs)
    error_message = "Se requiere una subred privada por zona."
  }
}

variable "db_subnets" {
  description = "Bloques de las subredes de datos, una por zona."
  type        = list(string)

  validation {
    condition     = length(var.db_subnets) == length(var.azs)
    error_message = "Se requiere una subred de datos por zona."
  }
}

variable "application_port" {
  description = "Puerto HTTP publicado por kind en la EC2, alcanzable solo desde el ALB."
  type        = number
  default     = 8080

  validation {
    condition     = var.application_port >= 1024 && var.application_port <= 65535
    error_message = "El puerto de aplicación debe estar entre 1024 y 65535."
  }
}
