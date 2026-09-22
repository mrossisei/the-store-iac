variable "network_name" {
  description = "Nombre de la red de Docker."
  type        = string
  default     = "kind"
}

variable "subnet" {
  description = "Bloque CIDR de la red."
  type        = string
}
