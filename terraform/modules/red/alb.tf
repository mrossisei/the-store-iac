# Único punto de entrada. Las EC2 se registran como destino en el módulo computo.
resource "aws_lb" "this" {
  name                       = var.name
  load_balancer_type         = "application"
  subnets                    = [for subnet in aws_subnet.public : subnet.id]
  security_groups            = [aws_security_group.alb.id]
  drop_invalid_header_fields = true

  tags = { Name = var.name }
}

resource "aws_lb_target_group" "ui" {
  name                 = "${var.name}-ui"
  vpc_id               = aws_vpc.this.id
  target_type          = "instance"
  protocol             = "HTTP"
  port                 = var.application_port
  deregistration_delay = 30

  health_check {
    path                = "/actuator/health/readiness"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = { Name = "${var.name}-ui" }
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
