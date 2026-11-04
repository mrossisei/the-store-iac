# La red es dueña de los SG compartidos: cómputo, datos y ALB consumen sus IDs.
# Las referencias entre reglas y grupos no producen un ciclo entre módulos.

locals {
  data_connections = {
    for connection in setproduct(var.db_subnets, [3306, 5432, 6379]) :
    "${connection[0]}:${connection[1]}" => { cidr = connection[0], port = connection[1] }
  }
}

# --- Grupos ----------------------------------------------------------------
resource "aws_security_group" "application" {
  name        = "${var.name}-kind-application"
  description = "EC2 privadas de The Store; ingreso HTTP solo desde ALB"
  vpc_id      = aws_vpc.this.id
  tags        = { Name = "${var.name}-kind-application" }
}

resource "aws_security_group" "alb" {
  name        = "${var.name}-kind-alb"
  description = "ALB publico de The Store"
  vpc_id      = aws_vpc.this.id
  tags        = { Name = "${var.name}-kind-alb" }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_egress_rule" "alb_application" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.application.id
  ip_protocol                  = "tcp"
  from_port                    = var.application_port
  to_port                      = var.application_port
}

resource "aws_vpc_security_group_ingress_rule" "application_from_alb" {
  security_group_id            = aws_security_group.application.id
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = var.application_port
  to_port                      = var.application_port
}

# HTTPS: SSM/ECR/APIs, HTTP(S): instalación de paquetes mediante NAT.
resource "aws_vpc_security_group_egress_rule" "application_web" {
  for_each = toset(["80", "443"])

  security_group_id = aws_security_group.application.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = tonumber(each.value)
  to_port           = tonumber(each.value)
}

resource "aws_vpc_security_group_egress_rule" "application_data" {
  for_each = local.data_connections

  security_group_id = aws_security_group.application.id
  cidr_ipv4         = each.value.cidr
  ip_protocol       = "tcp"
  from_port         = each.value.port
  to_port           = each.value.port
}

# AmazonProvidedDNS no se filtra con SG; se documenta el destino para otros resolvers.
resource "aws_vpc_security_group_egress_rule" "application_dns" {
  for_each = toset(["tcp", "udp"])

  security_group_id = aws_security_group.application.id
  cidr_ipv4         = "${cidrhost(var.cidr, 2)}/32"
  ip_protocol       = each.value
  from_port         = 53
  to_port           = 53
}

# --- VPC Endpoints de tipo Interface ---------------------------------------
resource "aws_security_group" "endpoints" {
  name        = "${var.name}-endpoints"
  description = "VPC Endpoints de tipo Interface: HTTPS desde la VPC"
  vpc_id      = aws_vpc.this.id

  tags = { Name = "${var.name}-endpoints" }
}

resource "aws_vpc_security_group_ingress_rule" "endpoints_https" {
  security_group_id            = aws_security_group.endpoints.id
  referenced_security_group_id = aws_security_group.application.id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
  description                  = "HTTPS desde la aplicacion (CIDR VPC solo en modo legacy)"
}
