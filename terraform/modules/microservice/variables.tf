variable "name" {
  description = "Nombre del microservicio (Deployment, Service, ServiceAccount, ConfigMap y DNS interno)."
  type        = string
}

variable "namespace" {
  description = "Namespace donde se despliega."
  type        = string
}

variable "image" {
  description = "Referencia completa de la imagen (registry/nombre:tag)."
  type        = string
}

variable "replicas" {
  description = "Cantidad de réplicas deseadas (si hay HPA, este valor es sólo el inicial)."
  type        = number
  default     = 1
}

variable "container_port" {
  description = "Puerto en el que escucha el proceso dentro del contenedor."
  type        = number
  default     = 8080
}

variable "service_port" {
  description = "Puerto del Service ClusterIP (los clientes usan http://<name>)."
  type        = number
  default     = 80
}

variable "env" {
  description = "Variables de entorno en texto plano (van a un ConfigMap)."
  type        = map(string)
  default     = {}
}

variable "env_from_field" {
  description = "Variables de entorno tomadas de la Downward API: nombre => fieldPath (ej. metadata.name)."
  type        = map(string)
  default     = {}
}

variable "secret_env" {
  description = "Variables de entorno tomadas de Secrets: nombre => { secret_name, key }."
  type = map(object({
    secret_name = string
    key         = string
  }))
  default = {}
}

variable "readiness_path" {
  description = "Path HTTP del readiness probe."
  type        = string
  default     = "/health"
}

variable "readiness_initial_delay" {
  description = "Segundos antes del primer readiness probe (las apps JVM tardan más en arrancar)."
  type        = number
  default     = 5
}

variable "resources" {
  description = "Requests y limits del contenedor."
  type = object({
    cpu_request    = string
    memory_request = string
    memory_limit   = string
  })
  default = {
    cpu_request    = "128m"
    memory_request = "256Mi"
    memory_limit   = "256Mi"
  }
}

variable "add_capabilities" {
  description = "Capabilities Linux a agregar (por defecto se quitan todas)."
  type        = list(string)
  default     = []
}

variable "autoscaling" {
  description = "Si se define, crea un HorizontalPodAutoscaler v2 por utilización de CPU."
  type = object({
    min_replicas       = number
    max_replicas       = number
    target_cpu_percent = number
  })
  default = null
}

variable "labels" {
  description = "Labels adicionales para todos los objetos (ej. tier, environment)."
  type        = map(string)
  default     = {}
}

variable "depends_on_services" {
  description = "Endpoints host[:puerto] (puerto 80 por defecto) que deben aceptar conexiones TCP antes de arrancar; se usa en un initContainer de espera. Vacía = sin espera."
  type        = list(string)
  default     = []
}
