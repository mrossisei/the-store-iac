output "vpc_id" {
  description = "ID de la VPC."
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "IDs de las subredes publicas, en el orden de azs."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs de las subredes privadas, en el orden de azs."
  value       = aws_subnet.private[*].id
}

output "db_subnet_ids" {
  description = "IDs de las subredes de datos, en el orden de azs."
  value       = aws_subnet.db[*].id
}

output "nat_public_ips" {
  description = "IPs publicas con las que salen a Internet las subredes privadas (una por zona)."
  value       = aws_eip.nat[*].public_ip
}

output "private_route_table_ids" {
  description = "Tablas de ruteo privadas, una por zona."
  value       = aws_route_table.private[*].id
}

output "db_route_table_id" {
  description = "Tabla de ruteo de las subredes de datos."
  value       = aws_route_table.db.id
}

output "application_security_group_id" {
  description = "Security group de las EC2 con kind."
  value       = aws_security_group.application.id
}

output "alb_security_group_id" {
  description = "Security group del ALB."
  value       = aws_security_group.alb.id
}

output "endpoint_security_group_id" {
  description = "Security group de los VPC Endpoints de tipo Interface."
  value       = aws_security_group.endpoints.id
}

output "gateway_endpoint_ids" {
  description = "IDs de los endpoints Gateway, por servicio."
  value       = { for service, endpoint in aws_vpc_endpoint.gateway : service => endpoint.id }
}

output "sqs_endpoint_id" {
  description = "ID del endpoint Interface de SQS."
  value       = aws_vpc_endpoint.sqs.id
}
