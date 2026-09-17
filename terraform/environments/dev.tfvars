# Entorno de desarrollo: liviano, sin estado, sin restricciones de red.
environment             = "dev"
hostname                = "dev.the-store.localhost"
persistence             = false
enable_network_policies = false
tls_enabled             = false
ui_theme                = "default"

replicas = {
  ui       = 1
  catalog  = 1
  carts    = 1
  orders   = 1
  checkout = 1
}

autoscaling_ui = null
