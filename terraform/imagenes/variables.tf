variable "release_manifest" {
  description = "Ruta del manifest generado por publicar-imagenes.py; null permite crear sólo repositorios."
  type        = string
  default     = null
}

variable "app_version" {
  description = "Tag a seleccionar y, con build_images, a construir y publicar."
  type        = string
  default     = null

  validation {
    condition     = var.app_version == null ? true : contains(["v1", "v2"], var.app_version)
    error_message = "app_version debe ser v1 o v2."
  }
}

variable "build_images" {
  description = "Construye y publica app_version en ECR. Las publicaciones existentes no se reescriben."
  type        = bool
  default     = false

  validation {
    condition     = !var.build_images || var.app_version != null
    error_message = "build_images requiere app_version."
  }
}
