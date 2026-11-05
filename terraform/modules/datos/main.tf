# ---------------------------------------------------------------------------
# Capa de datos, con servicios administrados de AWS:
#   catalog  -> RDS MySQL            orders -> RDS PostgreSQL + cola SQS
#   checkout -> ElastiCache (Redis)  carts  -> tabla DynamoDB
#
# RDS y ElastiCache viven en las subredes de datos (sin ruta a Internet), en
# modo Multi-AZ (instancia primaria en una zona y replica sincronica en la
# otra, con conmutacion automatica), y solo aceptan conexiones desde las EC2
# (security group). DynamoDB y SQS usan LabRole existente.
# Este módulo no crea políticas ni attachments IAM.
# ---------------------------------------------------------------------------
# Contrasenas generadas por Terraform: no hay credenciales escritas en el codigo.
resource "random_password" "mysql" {
  length  = 20
  special = false
}

resource "random_password" "postgres" {
  length  = 20
  special = false
}

# --- Red de la capa de datos -----------------------------------------------
resource "aws_db_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.subnet_ids
}

resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.name}-kind"
  subnet_ids = var.subnet_ids
}

# Firewall de las bases: solo se aceptan conexiones desde las EC2.
resource "aws_security_group" "data" {
  name        = "${var.name}-data"
  description = "Bases de datos de The Store: acceso solo desde los nodos del cluster"
  vpc_id      = var.vpc_id

  tags = { Name = "${var.name}-data" }
}

resource "aws_vpc_security_group_ingress_rule" "from_nodes" {
  for_each = { mysql = 3306, postgres = 5432, redis = 6379 }

  security_group_id            = aws_security_group.data.id
  referenced_security_group_id = var.application_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = each.value
  to_port                      = each.value
  description                  = "${each.key} desde los nodos del cluster"
}

# --- Bases relacionales (RDS) ----------------------------------------------
resource "aws_db_instance" "catalog" {
  identifier     = "${var.name}-catalog"
  engine         = "mysql"
  engine_version = var.mysql_engine_version
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp2"
  storage_encrypted = true

  db_name  = "catalogdb"
  username = "catalog"
  password = random_password.mysql.result

  db_subnet_group_name         = aws_db_subnet_group.this.name
  vpc_security_group_ids       = [aws_security_group.data.id]
  publicly_accessible          = false
  multi_az                     = true
  monitoring_interval          = 0
  performance_insights_enabled = false
  auto_minor_version_upgrade   = false
  engine_lifecycle_support     = "open-source-rds-extended-support-disabled"

  # Ajustes de POC: sin backups automaticos ni snapshot final, para que el
  # destroy sea rapido y no deje nada.
  backup_retention_period = 0
  skip_final_snapshot     = true
  deletion_protection     = false
  apply_immediately       = true
}

resource "aws_db_instance" "orders" {
  identifier     = "${var.name}-orders"
  engine         = "postgres"
  engine_version = var.postgres_engine_version
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp2"
  storage_encrypted = true

  db_name  = "orders"
  username = "orders"
  password = random_password.postgres.result

  db_subnet_group_name         = aws_db_subnet_group.this.name
  vpc_security_group_ids       = [aws_security_group.data.id]
  publicly_accessible          = false
  multi_az                     = true
  monitoring_interval          = 0
  performance_insights_enabled = false
  auto_minor_version_upgrade   = false
  engine_lifecycle_support     = "open-source-rds-extended-support-disabled"

  backup_retention_period = 0
  skip_final_snapshot     = true
  deletion_protection     = false
  apply_immediately       = true
}

# --- Cache (ElastiCache Redis) ---------------------------------------------
# Grupo de replicacion de dos nodos (primario + replica en la otra zona).
resource "aws_elasticache_replication_group" "checkout" {
  replication_group_id = "${var.name}-checkout"
  description          = "Cache del servicio checkout de The Store"
  engine               = "redis"
  engine_version       = var.redis_engine_version
  parameter_group_name = "default.redis7"
  node_type            = var.cache_node_type
  port                 = 6379

  num_cache_clusters          = 2
  multi_az_enabled            = true
  automatic_failover_enabled  = true
  preferred_cache_cluster_azs = var.availability_zones
  at_rest_encryption_enabled  = true
  transit_encryption_enabled  = false
  snapshot_retention_limit    = 0
  apply_immediately           = true

  subnet_group_name  = aws_elasticache_subnet_group.this.name
  security_group_ids = [aws_security_group.data.id]
}

# --- DynamoDB (carrito) ----------------------------------------------------
# El esquema es el que espera el servicio carts: clave "id" e indice global
# por "customerId".
resource "aws_dynamodb_table" "carts" {
  name         = "${var.name}-carts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "customerId"
    type = "S"
  }

  global_secondary_index {
    name            = "idx_global_customerId"
    projection_type = "ALL"

    key_schema {
      attribute_name = "customerId"
      key_type       = "HASH"
    }
  }
}

# --- SQS (eventos de ordenes) ----------------------------------------------
resource "aws_sqs_queue" "orders" {
  name = "${var.name}-orders"
}
