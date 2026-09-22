# ---------------------------------------------------------------------------
# Variables de entrada. Sus valores estan en terraform.tfvars.
# ---------------------------------------------------------------------------

# ----- Generales -----------------------------------------------------------
variable "project" {
  description = "Nombre del proyecto; se usa como prefijo de todos los recursos y como nombre del cluster."
  type        = string
  default     = "the-store"
}

variable "region" {
  description = "Region de AWS donde se despliega todo."
  type        = string
  default     = "us-east-1"
}

variable "availability_zones" {
  description = "Zonas de disponibilidad a usar (una subred publica y una privada en cada una)."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# ----- Red -----------------------------------------------------------------
variable "vpc_cidr" {
  description = "Bloque CIDR de la VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnets" {
  description = "Bloques de las subredes publicas (balanceador y NAT Gateway), una por zona."
  type        = list(string)
  default     = ["10.0.0.0/24", "10.0.1.0/24"]
}

variable "private_subnets" {
  description = "Bloques de las subredes privadas (nodos, pods y bases de datos), una por zona."
  type        = list(string)
  default     = ["10.0.16.0/20", "10.0.32.0/20"]
}

variable "service_cidr" {
  description = "Bloque de las IPs virtuales (ClusterIP) de los Services de Kubernetes."
  type        = string
  default     = "172.20.0.0/16"
}

# ----- Cluster -------------------------------------------------------------
variable "kubernetes_version" {
  description = "Version de Kubernetes del cluster EKS."
  type        = string
  default     = "1.34"
}

variable "node_instance_type" {
  description = "Tipo de instancia EC2 de los nodos worker."
  type        = string
  default     = "t3.medium"
}

variable "node_count" {
  description = "Cantidad de nodos worker. Cambiarla escala el grupo de nodos."
  type        = number
  default     = 2
}

# ----- Bases de datos ------------------------------------------------------
variable "db_instance_class" {
  description = "Tipo de instancia de las bases RDS (MySQL y PostgreSQL)."
  type        = string
  default     = "db.t3.micro"
}

variable "cache_node_type" {
  description = "Tipo de nodo de ElastiCache (Redis)."
  type        = string
  default     = "cache.t3.micro"
}

# ----- Aplicacion ----------------------------------------------------------
variable "namespace" {
  description = "Namespace de Kubernetes donde se despliega la aplicacion."
  type        = string
  default     = "the-store"
}

variable "app_version" {
  description = "Tag de las imagenes de los microservicios. Cambiarlo dispara un rolling update."
  type        = string
  default     = "1.0"
}

variable "replicas" {
  description = "Cantidad de replicas de cada microservicio (los no indicados quedan en 1)."
  type        = map(number)
  default     = {}
}

variable "ui_theme" {
  description = "Tema visual de la interfaz: default, green u orange."
  type        = string
  default     = "default"
}

variable "quarantine" {
  description = "Microservicios a aislar de la red ante un incidente de seguridad, por ejemplo [\"checkout\"]."
  type        = list(string)
  default     = []
}
