# Los SG pertenecen al módulo red; el ALB solo consume el SG ya restringido.
resource "aws_lb" "this" {
  name                       = "${var.name}-kind"
  internal                   = false
  load_balancer_type         = "application"
  ip_address_type            = "ipv4"
  subnets                    = values(var.public_subnet_ids)
  security_groups            = [var.alb_security_group_id]
  drop_invalid_header_fields = true
  enable_deletion_protection = false

  tags = { Name = "${var.name}-kind" }
}

resource "aws_lb_target_group" "ui" {
  name                 = "${var.name}-kind-ui"
  vpc_id               = var.vpc_id
  target_type          = "instance"
  protocol             = "HTTP"
  port                 = var.application_port
  deregistration_delay = 30

  health_check {
    enabled             = true
    protocol            = "HTTP"
    port                = "traffic-port"
    path                = "/actuator/health/readiness"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = { Name = "${var.name}-kind-ui" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ui.arn
  }
}

resource "aws_lb_target_group_attachment" "kind" {
  for_each         = var.instance_ids
  target_group_arn = aws_lb_target_group.ui.arn
  target_id        = each.value
  port             = var.application_port
}
