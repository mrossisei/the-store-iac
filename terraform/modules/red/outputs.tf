output "vpc_id" {
  description = "ID de la VPC."
  value       = aws_vpc.this.id
}

output "private_subnet_ids" {
  description = "Subredes privadas, por zona."
  value       = { for key, subnet in aws_subnet.private : key => subnet.id }
}

output "db_subnet_ids" {
  description = "Subredes de datos, por zona."
  value       = { for key, subnet in aws_subnet.db : key => subnet.id }
}

output "application_security_group_id" {
  description = "Security group de las EC2."
  value       = aws_security_group.application.id
}

output "target_group_arn" {
  description = "Target group de la UI."
  value       = aws_lb_target_group.ui.arn
}

output "alb_dns_name" {
  description = "Nombre DNS público del ALB."
  value       = aws_lb.this.dns_name
}
