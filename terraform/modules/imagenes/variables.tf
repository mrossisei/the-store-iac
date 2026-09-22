variable "name" {
  description = "Prefijo de los repositorios ECR."
  type        = string
}

variable "services" {
  description = "Servicios a construir: nombre => carpeta del codigo fuente."
  type        = map(string)
}

variable "source_root" {
  description = "Directorio raiz del codigo fuente de la aplicacion."
  type        = string
}

variable "app_version" {
  description = "Tag de las imagenes."
  type        = string
}
