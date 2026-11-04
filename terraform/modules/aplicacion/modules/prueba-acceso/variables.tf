variable "cluster_key" {
  description = "Clave del kind: a o b."
  type        = string
}

variable "cluster_uid" {
  description = "UID comprobado del clúster."
  type        = string
}

variable "value" {
  description = "Valor escrito en el ConfigMap de prueba."
  type        = string
}
