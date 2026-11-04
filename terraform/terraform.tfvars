project = "the-store"
region  = "us-east-1"

vpc_cidr = "10.0.0.0/16"
zones = {
  a = { availability_zone = "us-east-1a", public_cidr = "10.0.1.0/24", private_cidr = "10.0.16.0/24", db_cidr = "10.0.48.0/24" }
  b = { availability_zone = "us-east-1b", public_cidr = "10.0.2.0/24", private_cidr = "10.0.32.0/24", db_cidr = "10.0.49.0/24" }
}

services       = { ui = "ui", catalog = "catalog", carts = "cart", orders = "orders", checkout = "checkout" }
image_versions = ["v1", "v2"]

ami_id                = "ami-0c230065b91270bc6"
instance_type         = "t3.large"
instance_profile_name = "LabInstanceProfile"

kind = {
  pod_cidr     = "10.244.0.0/16"
  service_cidr = "172.20.0.0/16"
  host_ui_port = 8080
  ui_node_port = 30080
}

db_instance_class = "db.t3.micro"
cache_node_type   = "cache.t3.micro"

# Casos de uso: cambiar estos valores y ejecutar plan y apply.
app_version = "v1"
replicas    = { ui = 2, catalog = 2, carts = 2, orders = 2, checkout = 2 }
quarantine  = []
