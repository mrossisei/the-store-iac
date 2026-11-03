# Casos de uso: estas variables gobiernan simultáneamente ambos kind.
enable_application = true
app_version        = "v1"
replicas           = { ui = 2, catalog = 2, carts = 2, orders = 2, checkout = 2 }
quarantine         = []
