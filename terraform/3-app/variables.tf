variable "environment" {
  description = "Nombre del entorno. Debe coincidir con el workspace de Terraform activo."
  type        = string

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment debe ser \"dev\" o \"prod\"."
  }
}

variable "hostname" {
  description = "Host HTTP con el que el Ingress enruta al entorno (name-based virtual hosting)."
  type        = string
}

variable "persistence" {
  description = "true = capa de datos real (MariaDB, PostgreSQL, Redis, RabbitMQ, DynamoDB Local); false = proveedores in-memory."
  type        = bool
  default     = false
}

variable "enable_network_policies" {
  description = "Aplica NetworkPolicies de denegación por defecto con permisos explícitos entre servicios."
  type        = bool
  default     = true
}

variable "tls_enabled" {
  description = "Genera un certificado autofirmado y habilita HTTPS en el Ingress."
  type        = bool
  default     = false
}

variable "ui_theme" {
  description = "Tema de la UI (default, green, orange). Útil para demostrar cambios de configuración con rolling update."
  type        = string
  default     = "default"

  validation {
    condition     = contains(["default", "green", "orange"], var.ui_theme)
    error_message = "ui_theme debe ser default, green u orange."
  }
}

variable "replicas" {
  description = "Réplicas por microservicio (los no indicados quedan en 1)."
  type        = map(number)
  default     = {}
}

variable "autoscaling_ui" {
  description = "HPA para la UI (null = sin autoscaling)."
  type = object({
    min_replicas       = number
    max_replicas       = number
    target_cpu_percent = number
  })
  default = null
}

variable "images" {
  description = "Override de imágenes por servicio (por defecto se usan las publicadas por la capa 2). Permite, por ejemplo, un rollback a un tag anterior."
  type        = map(string)
  default     = {}
}

variable "storage_size" {
  description = "Tamaño del volumen persistente de cada datastore."
  type        = string
  default     = "1Gi"
}

variable "platform_state_path" {
  type    = string
  default = "../1-platform/terraform.tfstate"
}

variable "images_state_path" {
  type    = string
  default = "../2-images/terraform.tfstate"
}
