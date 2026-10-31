mock_provider "aws" {
  mock_resource "aws_lb" {
    defaults = { arn = "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/the-store-test/50dc6c495c0c9188", dns_name = "the-store-test.us-east-1.elb.amazonaws.com" }
  }
  mock_resource "aws_lb_target_group" {
    defaults = { arn = "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/the-store-test/73e2d6bc24d8a067" }
  }
}

run "alb_directo" {
  command = apply
  module { source = "../modules/alb" }
  variables {
    name                  = "the-store-test"
    vpc_id                = "vpc-00000000000000001"
    public_subnet_ids     = { a = "subnet-00000000000000001", b = "subnet-00000000000000002" }
    alb_security_group_id = "sg-00000000000000001"
    instance_ids          = { a = "i-00000000000000001", b = "i-00000000000000002" }
    application_port      = 8080
  }
  assert {
    condition     = !aws_lb.this.internal && aws_lb.this.load_balancer_type == "application" && aws_lb.this.ip_address_type == "ipv4" && aws_lb.this.subnets == toset(["subnet-00000000000000001", "subnet-00000000000000002"]) && aws_lb.this.security_groups == toset(["sg-00000000000000001"])
    error_message = "ALB público en ambas subredes públicas y con el SG de red."
  }
  assert {
    condition     = aws_lb_target_group.ui.target_type == "instance" && aws_lb_target_group.ui.port == 8080 && aws_lb_target_group.ui.protocol == "HTTP" && aws_lb_target_group.ui.vpc_id == "vpc-00000000000000001"
    error_message = "El ALB debe apuntar directamente a EC2:8080 dentro de la VPC."
  }
  assert {
    condition     = one(aws_lb_target_group.ui.health_check).path == "/actuator/health/readiness" && one(aws_lb_target_group.ui.health_check).matcher == "200" && one(aws_lb_target_group.ui.health_check).port == "traffic-port" && one(aws_lb_target_group.ui.health_check).protocol == "HTTP"
    error_message = "Health check de readiness en el mismo puerto HTTP; redirecciones no cuentan como Ready."
  }
  assert {
    condition     = aws_lb_listener.http.port == 80 && aws_lb_listener.http.protocol == "HTTP" && one(aws_lb_listener.http.default_action).type == "forward" && one(aws_lb_listener.http.default_action).target_group_arn == aws_lb_target_group.ui.arn
    error_message = "Listener HTTP/80 debe reenviar al target group de UI."
  }
  assert {
    condition     = keys(aws_lb_target_group_attachment.kind) == ["a", "b"] && aws_lb_target_group_attachment.kind["a"].target_id == "i-00000000000000001" && aws_lb_target_group_attachment.kind["b"].target_id == "i-00000000000000002" && alltrue([for target in aws_lb_target_group_attachment.kind : target.port == 8080 && target.target_group_arn == aws_lb_target_group.ui.arn])
    error_message = "Deben registrarse ambas instancias a/b con sus IDs correctos."
  }
}

run "contrato_alb_infra" {
  command = apply
  assert {
    condition     = output.url == "http://${module.alb.dns_name}" && output.load_balancer.target_ids == { for key, value in output.compute : key => value.instance_id }
    error_message = "URL desde el recurso ALB y attachments coherentes con compute."
  }
}
