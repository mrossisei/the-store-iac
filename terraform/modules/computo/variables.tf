variable "private_subnet_ids" {
  description = "Subred privada de cada EC2, con claves a/b."
  type        = map(string)

  validation {
    condition     = toset(keys(var.private_subnet_ids)) == toset(["a", "b"])
    error_message = "Se requieren las subredes privadas a y b."
  }
}

variable "application_security_group_id" {
  description = "Security group de las EC2, creado por el módulo red."
  type        = string
}

variable "instance_profile_name" {
  description = "Perfil de instancia existente (LabInstanceProfile)."
  type        = string
}

variable "ami_id" {
  description = "AMI fijada de las EC2."
  type        = string
}

variable "instance_type" {
  description = "Tipo de instancia; AWS Academy admite hasta large."
  type        = string
}

variable "environment" {
  description = "Contenido de config/entorno.json. Se copia completo al user-data: cambiar su forma reemplaza las EC2."
  type        = any
}

variable "tools" {
  description = "Contenido de config/herramientas.json; al host solo llegan las claves de local.bootstrap_tools."
  type        = any
}
