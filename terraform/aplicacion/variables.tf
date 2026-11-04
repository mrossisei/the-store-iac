variable "access_manifest" {
  description = "Manifest privado y temporal producido por scripts/acceso.py run; obligatorio incluso al destruir."
  type        = string
  nullable    = false

  validation {
    condition     = length(trimspace(var.access_manifest)) > 0
    error_message = "Iniciar scripts/acceso.py run para configurar ambos túneles."
  }
}

variable "enable_application" {
  description = "Despliega ambos juegos completos; false conserva compatibilidad con la sonda T04."
  type        = bool
  default     = false
}

variable "enable_network_policies" {
  description = "Activa segmentación y cuarentena en ambos kind cuando la aplicación está habilitada."
  type        = bool
  default     = true
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

variable "state_bucket" {
  description = "Bucket del estado infra; null reutiliza el backend inicializado de esta raíz."
  type        = string
  default     = null
}

variable "namespace" {
  description = "Namespace de la aplicación en ambos kind."
  type        = string
  default     = "the-store"
}

variable "app_version" {
  description = "Publicación a desplegar; nunca se compila al desplegar."
  type        = string
  default     = "v1"

  validation {
    condition     = contains(["v1", "v2"], var.app_version)
    error_message = "Elegir una publicación existente v1 o v2; nunca se compila al desplegar."
  }
}

variable "replicas" {
  description = "Réplicas de cada microservicio, iguales en ambos kind."
  type        = map(number)
  default     = { ui = 2, catalog = 2, carts = 2, orders = 2, checkout = 2 }

  validation {
    condition     = toset(keys(var.replicas)) == toset(["ui", "catalog", "carts", "orders", "checkout"]) && alltrue([for count in values(var.replicas) : count >= 1 && count <= 4 && floor(count) == count])
    error_message = "Definir réplicas enteras 1..4 para los cinco servicios."
  }
}

variable "quarantine" {
  description = "Microservicios aislados por NetworkPolicies, por ejemplo [\"checkout\"]."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for s in var.quarantine : contains(["ui", "catalog", "carts", "orders", "checkout"], s)])
    error_message = "Solo pueden aislarse servicios del contrato."
  }
}
