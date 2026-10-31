variable "name" {
  description = "Nombre de la VPC (y del cluster que la usa)."
  type        = string
}

variable "cidr" {
  description = "Bloque CIDR de la VPC."
  type        = string
}

variable "azs" {
  description = "Zonas de disponibilidad."
  type        = list(string)
}

variable "public_subnets" {
  description = "Bloques de las subredes publicas, una por zona."
  type        = list(string)
}

variable "private_subnets" {
  description = "Bloques de las subredes privadas, una por zona."
  type        = list(string)
}

variable "db_subnets" {
  description = "Bloques de las subredes de datos, una por zona."
  type        = list(string)
}

variable "region" {
  description = "Region (para los nombres de los VPC Endpoints)."
  type        = string
}

variable "create_application_security_groups" {
  description = "Crea los SG EC2/ALB del camino kind y restringe SQS al SG EC2. False conserva el consumidor EKS histórico."
  type        = bool
  default     = false
}

variable "application_port" {
  description = "Puerto HTTP publicado por kind en la EC2, alcanzable solo desde ALB."
  type        = number
  default     = 8080
  validation {
    condition     = var.application_port >= 1024 && var.application_port <= 65535
    error_message = "El puerto de aplicación debe estar entre 1024 y 65535."
  }
}
