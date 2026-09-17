variable "docker_host" {
  description = "Endpoint del daemon de Docker."
  type        = string
  default     = "unix:///var/run/docker.sock"
}

variable "platform_state_path" {
  description = "Ruta al estado de la capa 1 (para leer la dirección del registry)."
  type        = string
  default     = "../1-platform/terraform.tfstate"
}

variable "source_root" {
  description = "Directorio raíz del código fuente de The Store (contiene un subdirectorio por servicio con su Dockerfile)."
  type        = string
  default     = "../../the-store/src"
}

variable "image_prefix" {
  description = "Prefijo del nombre de las imágenes: <registry>/<prefix>-<servicio>:<tag>."
  type        = string
  default     = "the-store"
}

variable "services" {
  description = "Servicios a construir: clave = nombre lógico (coincide con el usado en la capa 3), valor = subdirectorio con el Dockerfile."
  type        = map(string)
  default = {
    ui       = "ui"
    catalog  = "catalog"
    carts    = "cart"
    orders   = "orders"
    checkout = "checkout"
  }
}

variable "keep_images_locally" {
  description = "Si es false, `terraform destroy` borra también las imágenes del daemon local."
  type        = bool
  default     = true
}
