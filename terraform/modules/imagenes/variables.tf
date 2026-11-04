variable "name" {
  description = "Prefijo de los repositorios."
  type        = string
}

variable "services" {
  description = "Microservicios: nombre => carpeta del código fuente."
  type        = map(string)
}
