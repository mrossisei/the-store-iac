# Los SG dejaron de ser condicionales al retirar EKS. Estos bloques conservan
# los recursos ya creados: Terraform solo actualiza su dirección en el estado.
moved {
  from = aws_security_group.application[0]
  to   = aws_security_group.application
}

moved {
  from = aws_security_group.alb[0]
  to   = aws_security_group.alb
}

moved {
  from = aws_vpc_security_group_ingress_rule.alb_http[0]
  to   = aws_vpc_security_group_ingress_rule.alb_http
}

moved {
  from = aws_vpc_security_group_egress_rule.alb_application[0]
  to   = aws_vpc_security_group_egress_rule.alb_application
}

moved {
  from = aws_vpc_security_group_ingress_rule.application_from_alb[0]
  to   = aws_vpc_security_group_ingress_rule.application_from_alb
}
