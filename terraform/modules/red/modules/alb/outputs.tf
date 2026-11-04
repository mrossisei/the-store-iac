output "arn" {
  description = "ARN del ALB."
  value       = aws_lb.this.arn
}

output "dns_name" {
  description = "Nombre DNS público del ALB."
  value       = aws_lb.this.dns_name
}

output "listener_arn" {
  description = "ARN del listener HTTP."
  value       = aws_lb_listener.http.arn
}

output "target_group_arn" {
  description = "ARN del target group de la UI."
  value       = aws_lb_target_group.ui.arn
}

output "target_ids" {
  description = "EC2 registradas, con claves a/b."
  value       = { for key, target in aws_lb_target_group_attachment.kind : key => target.target_id }
}
