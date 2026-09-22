variable "cluster_name" {
  description = "Nombre del cluster."
  type        = string
}

variable "network_name" {
  description = "Red de Docker en la que se crean los nodos."
  type        = string
}

variable "worker_count" {
  description = "Cantidad de nodos worker."
  type        = number
  default     = 2
}

variable "pod_subnet" {
  description = "Bloque CIDR de los pods."
  type        = string
}

variable "service_subnet" {
  description = "Bloque CIDR de los Services."
  type        = string
}

variable "node_image" {
  description = "Imagen de los nodos (fija la version de Kubernetes)."
  type        = string
  default     = "kindest/node:v1.35.0"
}

variable "ingress_chart_version" {
  description = "Version del chart de ingress-nginx."
  type        = string
  default     = "4.15.1"
}
