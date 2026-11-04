# Red de tres capas en cada zona:
#   - Pública: ALB y NAT Gateway, con ruta al Internet Gateway.
#   - Privada: EC2 con kind, sale a Internet por el NAT de su zona.
#   - Datos: RDS y ElastiCache, solo con la ruta local de la VPC.
resource "aws_vpc" "this" {
  cidr_block           = var.cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = var.name }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = { Name = var.name }
}

# --- Subredes --------------------------------------------------------------
resource "aws_subnet" "public" {
  for_each = var.zones

  vpc_id            = aws_vpc.this.id
  cidr_block        = each.value.public_cidr
  availability_zone = each.value.availability_zone

  tags = { Name = "${var.name}-public-${each.key}" }
}

resource "aws_subnet" "private" {
  for_each = var.zones

  vpc_id            = aws_vpc.this.id
  cidr_block        = each.value.private_cidr
  availability_zone = each.value.availability_zone

  tags = { Name = "${var.name}-private-${each.key}" }
}

resource "aws_subnet" "db" {
  for_each = var.zones

  vpc_id            = aws_vpc.this.id
  cidr_block        = each.value.db_cidr
  availability_zone = each.value.availability_zone

  tags = { Name = "${var.name}-db-${each.key}" }
}

# --- NAT Gateways: uno por zona --------------------------------------------
resource "aws_eip" "nat" {
  for_each = var.zones

  domain = "vpc"

  tags = { Name = "${var.name}-nat-${each.key}" }
}

resource "aws_nat_gateway" "this" {
  for_each = var.zones

  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = aws_subnet.public[each.key].id

  tags = { Name = "${var.name}-${each.key}" }

  depends_on = [aws_internet_gateway.this]
}

# --- Tablas de ruteo -------------------------------------------------------
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = { Name = "${var.name}-public" }
}

resource "aws_route_table" "private" {
  for_each = var.zones

  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this[each.key].id
  }

  tags = { Name = "${var.name}-private-${each.key}" }
}

# Sin ruta por defecto: solo la ruta local de la VPC.
resource "aws_route_table" "db" {
  vpc_id = aws_vpc.this.id

  tags = { Name = "${var.name}-db" }
}

resource "aws_route_table_association" "public" {
  for_each = var.zones

  subnet_id      = aws_subnet.public[each.key].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  for_each = var.zones

  subnet_id      = aws_subnet.private[each.key].id
  route_table_id = aws_route_table.private[each.key].id
}

resource "aws_route_table_association" "db" {
  for_each = var.zones

  subnet_id      = aws_subnet.db[each.key].id
  route_table_id = aws_route_table.db.id
}

# --- VPC Endpoints ---------------------------------------------------------
# Gateway, sin costo: S3 (capas de ECR) y DynamoDB (Cart) no pasan por el NAT.
resource "aws_vpc_endpoint" "gateway" {
  for_each = toset(["s3", "dynamodb"])

  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.region}.${each.key}"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [for table in aws_route_table.private : table.id]

  tags = { Name = "${var.name}-${each.key}" }
}

# Interface: con DNS privado, el nombre público de SQS resuelve a estas IPs.
resource "aws_vpc_endpoint" "sqs" {
  vpc_id              = aws_vpc.this.id
  service_name        = "com.amazonaws.${var.region}.sqs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [for subnet in aws_subnet.private : subnet.id]
  security_group_ids  = [aws_security_group.endpoints.id]
  private_dns_enabled = true

  tags = { Name = "${var.name}-sqs" }
}
