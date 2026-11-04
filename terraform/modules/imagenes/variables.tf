variable "name" {
  description = "Prefijo de los repositorios."
  type        = string
}

variable "services" {
  description = "Microservicios: nombre => carpeta del código fuente."
  type        = map(string)
}

variable "versions" {
  description = "Versiones a construir y publicar."
  type        = set(string)
}

variable "source_root" {
  description = "Carpeta raíz del código fuente."
  type        = string
}
