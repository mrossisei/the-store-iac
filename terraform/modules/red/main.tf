# ---------------------------------------------------------------------------
# Red: una VPC con dos zonas de disponibilidad y, en cada una, una subred
# publica y una privada.
#
#   - Subredes publicas: tienen ruta directa al Internet Gateway. Alojan el
#     balanceador de carga y el NAT Gateway.
#   - Subredes privadas: sin IP publica. Alojan los nodos del cluster (y sus
#     pods, que toman IPs de la misma subred). Salen a Internet a traves del
#     NAT Gateway (SNAT), pero nadie puede entrar desde afuera.
#   - Subredes de datos: alojan RDS y ElastiCache. No tienen ninguna ruta hacia
#     Internet: solo se alcanzan desde adentro de la VPC.
#
# Es la version en AWS de un diseno clasico de tres capas (DMZ, aplicacion y
# datos), separadas por las tablas de ruteo y los security groups. S3 y
# DynamoDB se alcanzan por VPC Endpoints de tipo Gateway, sin pasar por el NAT.
# ---------------------------------------------------------------------------
terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}

resource "aws_vpc" "this" {
  cidr_block           = var.cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = var.name }
}

# Puerta de salida/entrada a Internet de la VPC.
resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = { Name = var.name }
}

# --- Subredes --------------------------------------------------------------
resource "aws_subnet" "public" {
  count = length(var.azs)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnets[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.name}-public-${var.azs[count.index]}"
    # Etiquetas que usa Kubernetes para elegir donde crear balanceadores.
    "kubernetes.io/role/elb"            = "1"
    "kubernetes.io/cluster/${var.name}" = "shared"
  }
}

resource "aws_subnet" "private" {
  count = length(var.azs)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnets[count.index]
  availability_zone = var.azs[count.index]

  tags = {
    Name                                = "${var.name}-private-${var.azs[count.index]}"
    "kubernetes.io/role/internal-elb"   = "1"
    "kubernetes.io/cluster/${var.name}" = "shared"
  }
}

# --- NAT Gateway -----------------------------------------------------------
# Uno solo (en la primera zona) para acotar el costo. En produccion se pondria
# uno por zona para tolerar la caida de una zona completa.
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = { Name = "${var.name}-nat" }
}

resource "aws_nat_gateway" "this" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = { Name = var.name }

  depends_on = [aws_internet_gateway.this]
}

# --- Tablas de ruteo -------------------------------------------------------
# Publicas: todo lo que no es la VPC sale por el Internet Gateway.
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = { Name = "${var.name}-public" }
}

resource "aws_route_table_association" "public" {
  count = length(var.azs)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Privadas: todo lo que no es la VPC sale por el NAT Gateway.
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this.id
  }

  tags = { Name = "${var.name}-private" }
}

resource "aws_route_table_association" "private" {
  count = length(var.azs)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# --- Subredes de datos -----------------------------------------------------
resource "aws_subnet" "db" {
  count = length(var.azs)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.db_subnets[count.index]
  availability_zone = var.azs[count.index]

  tags = { Name = "${var.name}-db-${var.azs[count.index]}" }
}

# Tabla de ruteo sin ruta por defecto: solo la ruta local de la VPC.
resource "aws_route_table" "db" {
  vpc_id = aws_vpc.this.id

  tags = { Name = "${var.name}-db" }
}

resource "aws_route_table_association" "db" {
  count = length(var.azs)

  subnet_id      = aws_subnet.db[count.index].id
  route_table_id = aws_route_table.db.id
}

# --- VPC Endpoints (Gateway) -----------------------------------------------
# Agregan a la tabla de ruteo privada una ruta hacia S3 y DynamoDB dentro de
# la red de AWS, en lugar de salir por el NAT Gateway. No tienen costo. S3 lo
# usan los nodos para descargar las capas de las imagenes de ECR; DynamoDB, el
# servicio carts.
resource "aws_vpc_endpoint" "gateway" {
  for_each = toset(["s3", "dynamodb"])

  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.region}.${each.key}"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = { Name = "${var.name}-${each.key}" }
}
