# ---------------------------------------------------------------------------
# Variables de entrada. Sus valores están en terraform.tfvars.
# ---------------------------------------------------------------------------
variable "cluster_name" {
  description = "Nombre del cluster de Kubernetes."
  type        = string
  default     = "the-store"
}

variable "namespace" {
  description = "Namespace de Kubernetes donde se despliega la aplicación."
  type        = string
  default     = "the-store"
}

variable "worker_count" {
  description = "Cantidad de nodos worker del cluster (además del control-plane)."
  type        = number
  default     = 2
}

variable "docker_subnet" {
  description = "Bloque CIDR de la red Docker donde viven los nodos del cluster."
  type        = string
  default     = "172.30.0.0/24"
}

variable "pod_subnet" {
  description = "Bloque CIDR desde el que Kubernetes asigna IPs a los pods."
  type        = string
  default     = "10.244.0.0/16"
}

variable "service_subnet" {
  description = "Bloque CIDR de las IPs virtuales (ClusterIP) de los Services."
  type        = string
  default     = "10.96.0.0/16"
}

variable "app_version" {
  description = "Tag de las imágenes de los microservicios. Cambiarlo dispara un rolling update."
  type        = string
  default     = "1.0"
}

variable "hostname" {
  description = "Nombre de host por el que se publica la tienda."
  type        = string
  default     = "the-store.localhost"
}

variable "replicas" {
  description = "Cantidad de réplicas de cada microservicio."
  type        = map(number)
  default     = {}
}

variable "ui_theme" {
  description = "Tema visual de la interfaz: default, green u orange."
  type        = string
  default     = "default"
}
