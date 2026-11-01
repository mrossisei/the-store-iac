variable "name" {
  description = "Prefijo de los recursos."
  type        = string
}

variable "vpc_id" {
  description = "VPC donde se crean las bases."
  type        = string
}

variable "subnet_ids" {
  description = "Subredes (de datos) para las bases."
  type        = list(string)
}

variable "node_security_group_id" {
  description = "Security group de los nodos del cluster, unico origen permitido."
  type        = string
}

variable "node_role_name" {
  description = "Compatibilidad de la interfaz histórica; sin uso. Este módulo no administra IAM."
  type        = string
  default     = null
}

variable "db_instance_class" {
  description = "Tipo de instancia RDS."
  type        = string
}

variable "cache_node_type" {
  description = "Tipo de nodo ElastiCache."
  type        = string
}

variable "mysql_engine_version" {
  type    = string
  default = "8.4.11"
}

variable "postgres_engine_version" {
  type    = string
  default = "17.11"
}

variable "redis_engine_version" {
  type    = string
  default = "7.1"
}

variable "availability_zones" {
  description = "Primaria/réplica Redis en dos AZ distintas de las subredes de datos."
  type        = list(string)
  default     = null
  validation {
    condition     = var.availability_zones == null ? true : length(var.availability_zones) == 2 && length(toset(var.availability_zones)) == 2
    error_message = "Se requieren dos zonas distintas."
  }
}
