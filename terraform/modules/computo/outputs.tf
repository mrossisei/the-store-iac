output "instance_ids" {
  description = "EC2 de cada zona."
  value       = { for key, instance in aws_instance.kind : key => instance.id }
}
