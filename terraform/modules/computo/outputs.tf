output "instance_ids" {
  description = "IDs de las EC2, con claves a/b."
  value       = { for key, instance in aws_instance.kind : key => instance.id }
}

output "private_ips" {
  description = "IPs privadas de las EC2, con claves a/b."
  value       = { for key, instance in aws_instance.kind : key => instance.private_ip }
}
