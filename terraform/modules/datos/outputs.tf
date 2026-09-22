# Datos de conexion que necesita la aplicacion.
output "connection" {
  description = "Endpoints y credenciales de la capa de datos."
  sensitive   = true
  value = {
    mysql_host        = aws_db_instance.catalog.address
    mysql_password    = random_password.mysql.result
    postgres_host     = aws_db_instance.orders.address
    postgres_password = random_password.postgres.result
    redis_host        = aws_elasticache_replication_group.checkout.primary_endpoint_address
    dynamodb_table    = aws_dynamodb_table.carts.name
    sqs_queue_url     = aws_sqs_queue.orders.url
  }
}

output "endpoints" {
  description = "Endpoints (sin credenciales) para mostrar en los outputs."
  value = {
    mysql    = "${aws_db_instance.catalog.address}:3306"
    postgres = "${aws_db_instance.orders.address}:5432"
    redis    = "${aws_elasticache_replication_group.checkout.primary_endpoint_address}:6379"
    dynamodb = aws_dynamodb_table.carts.name
    sqs      = aws_sqs_queue.orders.url
  }
}
