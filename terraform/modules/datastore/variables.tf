variable "name" {
  description = "Nombre del datastore (StatefulSet, Service y DNS interno)."
  type        = string
}

variable "namespace" {
  type = string
}

variable "image" {
  description = "Imagen del motor de datos (ej. postgres:17-alpine)."
  type        = string
}

variable "port" {
  description = "Puerto principal del servicio."
  type        = number
}

variable "extra_ports" {
  description = "Puertos adicionales expuestos por el Service (ej. consola de administración)."
  type        = map(number)
  default     = {}
}

variable "env" {
  description = "Variables de entorno en texto plano."
  type        = map(string)
  default     = {}
}

variable "secret_env" {
  description = "Variables de entorno sensibles (van a un Secret propio del datastore)."
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "args" {
  description = "Argumentos del contenedor (opcional)."
  type        = list(string)
  default     = null
}

variable "data_path" {
  description = "Directorio donde el motor persiste sus datos (se monta el PVC)."
  type        = string
}

variable "storage_size" {
  description = "Tamaño del PersistentVolumeClaim."
  type        = string
  default     = "1Gi"
}

variable "storage_class" {
  description = "StorageClass a usar (kind provee 'standard' con local-path-provisioner)."
  type        = string
  default     = "standard"
}

variable "readiness_command" {
  description = "Comando del readiness probe (exec). Si es null se usa un chequeo TCP al puerto."
  type        = list(string)
  default     = null
}

variable "resources" {
  type = object({
    cpu_request    = string
    memory_request = string
    memory_limit   = string
  })
  default = {
    cpu_request    = "100m"
    memory_request = "256Mi"
    memory_limit   = "512Mi"
  }
}

variable "run_as_user" {
  description = "UID con el que corre el contenedor (null = el que define la imagen)."
  type        = number
  default     = null
}

variable "fs_group" {
  description = "GID propietario del volumen de datos (null = no forzar)."
  type        = number
  default     = null
}

variable "labels" {
  type    = map(string)
  default = {}
}
