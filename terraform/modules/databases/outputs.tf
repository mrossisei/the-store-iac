# Datos de conexion que necesita la aplicacion.
output "connection" {
  description = "Endpoints y credenciales de las bases de datos."
  sensitive   = true
  value = {
    mysql_host        = kubernetes_service_v1.db["catalog-db"].metadata[0].name
    mysql_password    = random_password.mysql.result
    postgres_host     = kubernetes_service_v1.db["orders-db"].metadata[0].name
    postgres_password = random_password.postgres.result
    redis_host        = kubernetes_service_v1.db["checkout-db"].metadata[0].name
  }
}
