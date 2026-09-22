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
