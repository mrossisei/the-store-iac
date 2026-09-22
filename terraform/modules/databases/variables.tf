variable "name" {
  description = "Prefijo de los recursos."
  type        = string
}

variable "vpc_id" {
  description = "VPC donde se crean las bases."
  type        = string
}

variable "subnet_ids" {
  description = "Subredes (privadas) para las bases."
  type        = list(string)
}

variable "node_security_group_id" {
  description = "Security group de los nodos del cluster, unico origen permitido."
  type        = string
}

variable "node_role_name" {
  description = "Rol de IAM de los nodos, al que se le dan permisos sobre DynamoDB y SQS."
  type        = string
}

variable "db_instance_class" {
  description = "Tipo de instancia RDS."
  type        = string
}

variable "cache_node_type" {
  description = "Tipo de nodo ElastiCache."
  type        = string
}
