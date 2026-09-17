locals {
  env       = var.environment
  namespace = "the-store-${local.env}"

  images = merge(data.terraform_remote_state.images.outputs.images, var.images)

  replicas = merge(
    { ui = 1, catalog = 1, carts = 1, orders = 1, checkout = 1 },
    var.replicas,
  )

  common_labels = {
    "app.kubernetes.io/part-of"  = "the-store"
    "the-store.itba/environment" = local.env
  }
  app_labels  = merge(local.common_labels, { "the-store.itba/tier" = "app" })
  data_labels = merge(local.common_labels, { "the-store.itba/tier" = "data" })

  java_opts = "-XX:MaxRAMPercentage=75.0 -Djava.security.egd=file:/dev/urandom"

  # Puertos de la capa de datos (también los usan las NetworkPolicies).
  ports = {
    mariadb  = 3306
    postgres = 5432
    redis    = 6379
    amqp     = 5672
    dynamodb = 8000
  }
}
