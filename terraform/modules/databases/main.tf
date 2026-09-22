# ---------------------------------------------------------------------------
# Capa de datos, con servicios administrados de AWS:
#   catalog  -> RDS MySQL            orders -> RDS PostgreSQL + cola SQS
#   checkout -> ElastiCache (Redis)  carts  -> tabla DynamoDB
#
# RDS y ElastiCache viven en las subredes privadas y solo aceptan conexiones
# desde los nodos del cluster (security group). DynamoDB y SQS son servicios
# regionales sin red propia: el acceso se controla con IAM, dandole permisos al
# rol de los nodos (que heredan los pods).
# ---------------------------------------------------------------------------
terraform {
  required_providers {
    aws    = { source = "hashicorp/aws" }
    random = { source = "hashicorp/random" }
  }
}

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
  name       = var.name
  subnet_ids = var.subnet_ids
}

# Firewall de las bases: solo se aceptan conexiones desde los nodos del cluster.
resource "aws_security_group" "data" {
  name        = "${var.name}-data"
  description = "Bases de datos de The Store: acceso solo desde los nodos del cluster"
  vpc_id      = var.vpc_id

  tags = { Name = "${var.name}-data" }
}

resource "aws_vpc_security_group_ingress_rule" "from_nodes" {
  for_each = { mysql = 3306, postgres = 5432, redis = 6379 }

  security_group_id            = aws_security_group.data.id
  referenced_security_group_id = var.node_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = each.value
  to_port                      = each.value
  description                  = "${each.key} desde los nodos del cluster"
}

# --- Bases relacionales (RDS) ----------------------------------------------
resource "aws_db_instance" "catalog" {
  identifier     = "${var.name}-catalog"
  engine         = "mysql"
  engine_version = "8.0"
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp3"

  db_name  = "catalogdb"
  username = "catalog"
  password = random_password.mysql.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.data.id]
  publicly_accessible    = false
  multi_az               = false

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
  engine_version = "17"
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp3"

  db_name  = "orders"
  username = "orders"
  password = random_password.postgres.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.data.id]
  publicly_accessible    = false
  multi_az               = false

  backup_retention_period = 0
  skip_final_snapshot     = true
  deletion_protection     = false
  apply_immediately       = true
}

# --- Cache (ElastiCache Redis) ---------------------------------------------
resource "aws_elasticache_cluster" "checkout" {
  cluster_id           = "${var.name}-checkout"
  engine               = "redis"
  engine_version       = "7.1"
  parameter_group_name = "default.redis7"
  node_type            = var.cache_node_type
  num_cache_nodes      = 1
  port                 = 6379

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

# --- Permisos de los pods sobre DynamoDB y SQS -----------------------------
data "aws_iam_policy_document" "data_access" {
  statement {
    sid = "Carts"
    actions = [
      "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem",
      "dynamodb:Query", "dynamodb:Scan", "dynamodb:DescribeTable",
      "dynamodb:BatchGetItem", "dynamodb:BatchWriteItem",
    ]
    resources = [aws_dynamodb_table.carts.arn, "${aws_dynamodb_table.carts.arn}/index/*"]
  }

  statement {
    sid       = "Orders"
    actions   = ["sqs:SendMessage", "sqs:GetQueueUrl", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.orders.arn]
  }
}

resource "aws_iam_policy" "data_access" {
  name   = "${var.name}-data-access"
  policy = data.aws_iam_policy_document.data_access.json
}

resource "aws_iam_role_policy_attachment" "nodes" {
  role       = var.node_role_name
  policy_arn = aws_iam_policy.data_access.arn
}
