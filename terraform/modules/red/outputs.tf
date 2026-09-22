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
