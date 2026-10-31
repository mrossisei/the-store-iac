variable "access_manifest" {
  description = "Manifest privado y temporal producido por scripts/acceso.py run; obligatorio incluso al destruir."
  type        = string
  nullable    = false
  validation {
    condition     = length(trimspace(var.access_manifest)) > 0
    error_message = "Iniciar scripts/acceso.py run para configurar ambos túneles."
  }
}

variable "enable_access_probe" {
  description = "Activa únicamente los objetos de prueba T04, uno por kind."
  type        = bool
  default     = false
}

variable "probe_value" {
  description = "Valor que permite verificar actualización y lectura del ConfigMap de prueba."
  type        = string
  default     = "initial"
}
