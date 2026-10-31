output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "db_subnet_ids" {
  value = aws_subnet.db[*].id
}

output "nat_public_ips" {
  description = "IPs publicas con las que salen a Internet las subredes privadas (una por zona)."
  value       = aws_eip.nat[*].public_ip
}

output "private_route_table_ids" {
  value = aws_route_table.private[*].id
}

output "db_route_table_id" {
  value = aws_route_table.db.id
}

output "application_security_group_id" {
  value = try(aws_security_group.application[0].id, null)
}

output "alb_security_group_id" {
  value = try(aws_security_group.alb[0].id, null)
}

output "endpoint_security_group_id" {
  value = aws_security_group.endpoints.id
}

output "gateway_endpoint_ids" {
  value = { for service, endpoint in aws_vpc_endpoint.gateway : service => endpoint.id }
}

output "sqs_endpoint_id" {
  value = aws_vpc_endpoint.sqs.id
}
