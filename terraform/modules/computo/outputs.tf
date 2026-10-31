output "instance_ids" {
  value = { for key, instance in aws_instance.kind : key => instance.id }
}
output "private_ips" {
  value = { for key, instance in aws_instance.kind : key => instance.private_ip }
}
