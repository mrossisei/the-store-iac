# ---------------------------------------------------------------------------
# Valores de configuracion del entorno. Cambiar algo aca y ejecutar
# `terraform apply` es la unica forma de modificar la infraestructura.
# ---------------------------------------------------------------------------
project            = "the-store"
region             = "us-east-1"
availability_zones = ["us-east-1a", "us-east-1b"]

# Red
vpc_cidr        = "10.0.0.0/16"
public_subnets  = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnets = ["10.0.16.0/20", "10.0.32.0/20"]
db_subnets      = ["10.0.48.0/24", "10.0.49.0/24"]
service_cidr    = "172.20.0.0/16"

# Cluster
kubernetes_version = "1.34"
node_instance_type = "t3.medium"
node_count         = 2

# Bases de datos
db_instance_class = "db.t3.micro"
cache_node_type   = "cache.t3.micro"

# Aplicacion
namespace   = "the-store"
app_version = "1.0"
ui_theme    = "default"

# Dos replicas de cada servicio, repartidas entre las dos zonas.
replicas = {
  ui       = 2
  catalog  = 2
  carts    = 2
  orders   = 2
  checkout = 2
}

# Servicios aislados de la red por un incidente (normalmente vacio).
quarantine = []
