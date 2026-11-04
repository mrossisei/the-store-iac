mock_provider "aws" {}
mock_provider "random" {}

run "datos_lab" {
  command = apply
  module { source = "../modules/datos" }
  variables {
    name                          = "the-store-test"
    vpc_id                        = "vpc-00000000000000001"
    subnet_ids                    = ["subnet-00000000000000001", "subnet-00000000000000002"]
    application_security_group_id = "sg-00000000000000001"
    db_instance_class             = "db.t3.micro"
    cache_node_type               = "cache.t3.micro"
    availability_zones            = ["us-east-1a", "us-east-1b"]
  }
  assert {
    condition = alltrue([for db in [aws_db_instance.catalog, aws_db_instance.orders] :
      db.multi_az && !db.publicly_accessible && db.storage_type == "gp2" && db.allocated_storage == 20 && db.storage_encrypted && db.monitoring_interval == 0 && !db.performance_insights_enabled && db.instance_class == "db.t3.micro" && db.vpc_security_group_ids == toset([aws_security_group.data.id])
    ])
    error_message = "RDS privadas Multi-AZ, gp2 acotado y sin Enhanced Monitoring; SG solo de datos."
  }
  assert {
    condition     = aws_db_instance.catalog.engine == "mysql" && aws_db_instance.catalog.engine_version == "8.4.11" && aws_db_instance.orders.engine == "postgres" && aws_db_instance.orders.engine_version == "17.11"
    error_message = "Motores/versiones deben coincidir con los comprobados en la cuenta."
  }
  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.from_nodes) == 3 && alltrue([for rule in aws_vpc_security_group_ingress_rule.from_nodes : rule.referenced_security_group_id == "sg-00000000000000001" && rule.cidr_ipv4 == null && rule.cidr_ipv6 == null && rule.from_port == rule.to_port && contains([3306, 5432, 6379], rule.from_port)])
    error_message = "Solo EC2 puede iniciar conexiones a los tres puertos de datos."
  }
  assert {
    condition     = aws_elasticache_replication_group.checkout.num_cache_clusters == 2 && aws_elasticache_replication_group.checkout.multi_az_enabled && aws_elasticache_replication_group.checkout.automatic_failover_enabled && aws_elasticache_replication_group.checkout.preferred_cache_cluster_azs == tolist(["us-east-1a", "us-east-1b"]) && aws_elasticache_replication_group.checkout.at_rest_encryption_enabled
    error_message = "Redis requiere primaria/réplica en AZ distintas con failover."
  }
  assert {
    condition     = aws_dynamodb_table.carts.hash_key == "id" && one(aws_dynamodb_table.carts.global_secondary_index).name == "idx_global_customerId" && one(one(aws_dynamodb_table.carts.global_secondary_index).key_schema).attribute_name == "customerId" && aws_sqs_queue.orders.name == "the-store-test-orders"
    error_message = "Conservar tabla/índice del carrito y cola compartida de Orders."
  }
  assert {
    condition     = issensitive(output.connection) && toset(keys(output.connection)) == toset(["mysql_host", "mysql_password", "postgres_host", "postgres_password", "redis_host", "dynamodb_table", "sqs_queue_url"])
    error_message = "Conservar el contrato sensible de conexión de la aplicación."
  }
}
