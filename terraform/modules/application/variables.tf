variable "namespace" {
  description = "Namespace donde se despliega la aplicacion."
  type        = string
}

variable "images" {
  description = "Imagen de cada microservicio."
  type        = map(string)
}

variable "replicas" {
  description = "Cantidad de copias de cada microservicio (por defecto 1)."
  type        = map(number)
  default     = {}
}

variable "hostname" {
  description = "Nombre de host por el que se publica la tienda."
  type        = string
}

variable "ui_theme" {
  description = "Tema visual de la interfaz."
  type        = string
  default     = "default"
}

variable "ingress_namespace" {
  description = "Namespace donde corre el Ingress Controller."
  type        = string
  default     = "ingress-nginx"
}

variable "databases" {
  description = "Datos de conexion a las bases de datos."
  sensitive   = true
  type = object({
    mysql_host        = string
    mysql_password    = string
    postgres_host     = string
    postgres_password = string
    redis_host        = string
  })
}

variable "quarantine" {
  description = "Microservicios aislados de la red por un incidente de seguridad (lista vacia = ninguno)."
  type        = list(string)
  default     = []
}
