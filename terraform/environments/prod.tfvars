# Entorno productivo: persistencia real, redundancia, autoscaling, TLS y
# segmentación de red.
environment             = "prod"
hostname                = "the-store.localhost"
persistence             = true
enable_network_policies = true
tls_enabled             = true
ui_theme                = "default"
storage_size            = "1Gi"

replicas = {
  ui       = 2
  catalog  = 2
  carts    = 1
  orders   = 1
  checkout = 1
}

autoscaling_ui = {
  min_replicas       = 2
  max_replicas       = 4
  target_cpu_percent = 70
}
