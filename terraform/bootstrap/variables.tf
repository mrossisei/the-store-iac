variable "region" {
  description = "Region donde se crea el bucket (la misma que el resto del proyecto)."
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Nombre del bucket de estado. Debe ser unico en todo AWS (ej: the-store-tfstate-<apellido>)."
  type        = string
}
