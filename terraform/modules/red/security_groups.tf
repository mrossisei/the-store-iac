# Internet llega al ALB, el ALB llega a las EC2 y las EC2 llegan a los datos.
locals {
  data_ports = [3306, 5432, 6379]
  data_rules = {
    for pair in setproduct([for zone in values(var.zones) : zone.db_cidr], local.data_ports) :
    "${pair[0]}:${pair[1]}" => { cidr = pair[0], port = pair[1] }
  }
}

resource "aws_security_group" "alb" {
  name        = "${var.name}-alb"
  description = "ALB publico de The Store"
  vpc_id      = aws_vpc.this.id

  tags = { Name = "${var.name}-alb" }
}

resource "aws_security_group" "application" {
  name        = "${var.name}-application"
  description = "EC2 privadas: HTTP solo desde el ALB"
  vpc_id      = aws_vpc.this.id

  tags = { Name = "${var.name}-application" }
}

resource "aws_security_group" "endpoints" {
  name        = "${var.name}-endpoints"
  description = "VPC Endpoints Interface: HTTPS desde las EC2"
  vpc_id      = aws_vpc.this.id

  tags = { Name = "${var.name}-endpoints" }
}

# --- ALB -------------------------------------------------------------------
resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_egress_rule" "alb_to_application" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.application.id
  ip_protocol                  = "tcp"
  from_port                    = var.application_port
  to_port                      = var.application_port
}

# --- EC2 -------------------------------------------------------------------
resource "aws_vpc_security_group_ingress_rule" "application_from_alb" {
  security_group_id            = aws_security_group.application.id
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = var.application_port
  to_port                      = var.application_port
}

# HTTP y HTTPS: paquetes, SSM, ECR y APIs de AWS.
resource "aws_vpc_security_group_egress_rule" "application_web" {
  for_each = toset(["80", "443"])

  security_group_id = aws_security_group.application.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = tonumber(each.value)
  to_port           = tonumber(each.value)
}

resource "aws_vpc_security_group_egress_rule" "application_data" {
  for_each = local.data_rules

  security_group_id = aws_security_group.application.id
  cidr_ipv4         = each.value.cidr
  ip_protocol       = "tcp"
  from_port         = each.value.port
  to_port           = each.value.port
}

# --- Endpoints -------------------------------------------------------------
resource "aws_vpc_security_group_ingress_rule" "endpoints_https" {
  security_group_id            = aws_security_group.endpoints.id
  referenced_security_group_id = aws_security_group.application.id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
}
