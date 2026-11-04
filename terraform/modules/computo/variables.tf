variable "name" {
  description = "Prefijo de las EC2 y sus clústeres."
  type        = string
}

variable "region" {
  description = "Región de AWS."
  type        = string
}

variable "private_subnet_ids" {
  description = "Subred privada de cada EC2, por zona."
  type        = map(string)
}

variable "application_security_group_id" {
  description = "Security group de las EC2."
  type        = string
}

variable "target_group_arn" {
  description = "Target group del ALB."
  type        = string
}

variable "instance_profile_name" {
  description = "Perfil de instancia existente."
  type        = string
}

variable "ami_id" {
  description = "AMI de las EC2."
  type        = string
}

variable "instance_type" {
  description = "Tipo de instancia."
  type        = string
}

variable "kind" {
  description = "Redes y puertos de kind."
  type = object({
    pod_cidr     = string
    service_cidr = string
    host_ui_port = number
    ui_node_port = number
  })
}
