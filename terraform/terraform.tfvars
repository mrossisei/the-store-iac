# ---------------------------------------------------------------------------
# Valores de configuración del entorno. Cambiar algo acá y ejecutar
# `terraform apply` es la única forma de modificar la infraestructura.
# ---------------------------------------------------------------------------
cluster_name = "the-store"
namespace    = "the-store"

# Infraestructura
worker_count   = 2
docker_subnet  = "172.30.0.0/24"
pod_subnet     = "10.244.0.0/16"
service_subnet = "10.96.0.0/16"

# Aplicación
app_version = "1.0"
hostname    = "the-store.localhost"
ui_theme    = "default"

replicas = {
  ui       = 2
  catalog  = 1
  carts    = 1
  orders   = 1
  checkout = 1
}

# Servicios aislados de la red por un incidente (normalmente vacio).
quarantine = []
