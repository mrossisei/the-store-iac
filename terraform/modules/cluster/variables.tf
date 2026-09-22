variable "name" {
  description = "Nombre del cluster."
  type        = string
}

variable "region" {
  description = "Region de AWS (la necesita el AWS Load Balancer Controller)."
  type        = string
}

variable "kubernetes_version" {
  description = "Version de Kubernetes."
  type        = string
}

variable "vpc_id" {
  description = "VPC donde se crea el cluster."
  type        = string
}

variable "subnet_ids" {
  description = "Subredes (privadas) para los nodos."
  type        = list(string)
}

variable "service_cidr" {
  description = "Bloque de las ClusterIP de los Services."
  type        = string
}

variable "node_instance_type" {
  description = "Tipo de instancia EC2 de los nodos."
  type        = string
}

variable "node_count" {
  description = "Cantidad de nodos worker."
  type        = number
}

variable "lb_controller_chart_version" {
  description = "Version del chart del AWS Load Balancer Controller."
  type        = string
  default     = "3.5.0"
}
