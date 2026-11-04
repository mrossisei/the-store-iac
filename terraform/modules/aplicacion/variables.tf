variable "namespace" {
  description = "Namespace donde se despliega la aplicacion."
  type        = string
  default     = "the-store"
}

variable "region" {
  description = "Region de AWS (la usan los SDK de los servicios que hablan con DynamoDB y SQS)."
  type        = string
}

variable "images" {
  description = "Imagen de cada microservicio."
  type        = map(string)
}

variable "replicas" {
  description = "Cantidad de copias de cada microservicio (por defecto 2)."
  type        = map(number)
  default     = {}
}

variable "ui_theme" {
  description = "Tema visual de la interfaz."
  type        = string
  default     = "default"
}

variable "databases" {
  description = "Datos de conexion a la capa de datos."
  sensitive   = true
  type = object({
    mysql_host        = string
    mysql_password    = string
    postgres_host     = string
    postgres_password = string
    redis_host        = string
    dynamodb_table    = string
    sqs_queue_url     = string
  })
}

variable "kind" {
  description = "Redes y puertos de kind."
  type = object({
    pod_cidr     = string
    service_cidr = string
    host_ui_port = number
    ui_node_port = number
  })
}

variable "quarantine" {
  description = "Servicios aislados retirando todos sus permisos; no modifica pods."
  type        = set(string)
  default     = []

  validation {
    condition     = alltrue([for app in var.quarantine : contains(["ui", "catalog", "carts", "orders", "checkout"], app)])
    error_message = "quarantine admite ui, catalog, carts, orders y checkout."
  }
}
