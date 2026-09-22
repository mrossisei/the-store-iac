variable "namespace" {
  description = "Namespace donde se despliega la aplicacion."
  type        = string
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

variable "quarantine" {
  description = "Microservicios aislados de la red por un incidente de seguridad (lista vacia = ninguno)."
  type        = list(string)
  default     = []
}

variable "ingress_cidrs" {
  description = "Bloques desde los que llega el trafico del balanceador (las subredes publicas)."
  type        = list(string)
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
