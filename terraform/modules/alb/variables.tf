variable "name" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,19}$", var.name))
    error_message = "Nombre de proyecto: 1 a 20 caracteres alfanuméricos/guiones, empezando por letra."
  }
}

variable "vpc_id" { type = string }
variable "alb_security_group_id" { type = string }

variable "public_subnet_ids" {
  type = map(string)
  validation {
    condition     = toset(keys(var.public_subnet_ids)) == toset(["a", "b"]) && length(toset(values(var.public_subnet_ids))) == 2
    error_message = "Se requieren dos subredes públicas distintas con claves a/b."
  }
}

variable "instance_ids" {
  type = map(string)
  validation {
    condition     = toset(keys(var.instance_ids)) == toset(["a", "b"]) && length(toset(values(var.instance_ids))) == 2
    error_message = "Se requieren dos instancias distintas con claves a/b."
  }
}

variable "application_port" {
  description = "Puerto del host EC2 publicado por kind, coincidente con las reglas SG de red."
  type        = number
  default     = 8080
  validation {
    condition     = var.application_port == floor(var.application_port) && var.application_port >= 1024 && var.application_port <= 65535
    error_message = "Puerto entero entre 1024 y 65535."
  }
}
