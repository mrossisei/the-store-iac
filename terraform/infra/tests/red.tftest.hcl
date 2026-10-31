mock_provider "aws" {}

run "red_kind" {
  command = apply
  module { source = "../modules/red" }
  variables {
    name                               = "the-store-test"
    region                             = "us-east-1"
    cidr                               = "10.0.0.0/16"
    azs                                = ["us-east-1a", "us-east-1b"]
    public_subnets                     = ["10.0.1.0/24", "10.0.2.0/24"]
    private_subnets                    = ["10.0.16.0/24", "10.0.32.0/24"]
    db_subnets                         = ["10.0.48.0/24", "10.0.49.0/24"]
    create_application_security_groups = true
  }
  assert {
    condition     = length(aws_subnet.public) == 2 && length(aws_subnet.private) == 2 && length(aws_subnet.db) == 2
    error_message = "Se requieren exactamente seis subredes."
  }
  assert {
    condition     = length(aws_nat_gateway.this) == 2 && one(aws_route_table.private[0].route).nat_gateway_id == aws_nat_gateway.this[0].id && one(aws_route_table.private[1].route).nat_gateway_id == aws_nat_gateway.this[1].id
    error_message = "Cada privada debe salir por el NAT de su propia AZ."
  }
  assert {
    condition     = length(aws_route_table.db.route) == 0
    error_message = "La tabla de datos no puede tener ruta por defecto."
  }
  assert {
    condition     = aws_subnet.private[0].cidr_block == "10.0.16.0/24" && aws_subnet.private[1].cidr_block == "10.0.32.0/24" && !aws_subnet.private[0].map_public_ip_on_launch && !aws_subnet.private[1].map_public_ip_on_launch
    error_message = "Privadas /24 y EC2 sin asignación pública automática."
  }
  assert {
    condition     = aws_vpc_endpoint.sqs.private_dns_enabled && aws_vpc_endpoint.sqs.vpc_endpoint_type == "Interface" && length(aws_vpc_endpoint.sqs.subnet_ids) == 2 && length(aws_vpc_endpoint.gateway) == 2 && length(aws_vpc_endpoint.gateway["s3"].route_table_ids) == 2 && length(aws_vpc_endpoint.gateway["dynamodb"].route_table_ids) == 2
    error_message = "Endpoints S3/DynamoDB en ambas rutas y SQS privado en ambas AZ."
  }
  assert {
    condition     = aws_vpc_security_group_ingress_rule.endpoints_https.cidr_ipv4 == null && aws_vpc_security_group_ingress_rule.endpoints_https.referenced_security_group_id == aws_security_group.application[0].id && aws_vpc_security_group_ingress_rule.endpoints_https.from_port == 443
    error_message = "SQS solo debe admitir HTTPS desde SG EC2, no desde toda la VPC."
  }
  assert {
    condition     = aws_vpc_security_group_ingress_rule.application_from_alb[0].referenced_security_group_id == aws_security_group.alb[0].id && aws_vpc_security_group_ingress_rule.application_from_alb[0].from_port == 8080 && aws_vpc_security_group_ingress_rule.application_from_alb[0].to_port == 8080 && aws_vpc_security_group_egress_rule.alb_application[0].referenced_security_group_id == aws_security_group.application[0].id
    error_message = "8080 debe conectar exclusivamente ALB con EC2."
  }
}

run "contrato_infra" {
  command = apply
  assert {
    condition     = keys(output.network.private_subnets) == ["a", "b"] && output.network.private_subnets.a.cidr == "10.0.16.0/24" && output.network.private_subnets.b.cidr == "10.0.32.0/24"
    error_message = "El consumidor debe recibir subredes identificadas por a/b."
  }
}
