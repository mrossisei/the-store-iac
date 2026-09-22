variable "namespace" {
  description = "Namespace donde se despliegan las bases."
  type        = string
}

variable "storage_size" {
  description = "Tamano del disco persistente de cada base."
  type        = string
  default     = "1Gi"
}
