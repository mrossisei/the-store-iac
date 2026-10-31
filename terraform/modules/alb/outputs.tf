output "arn" { value = aws_lb.this.arn }
output "dns_name" { value = aws_lb.this.dns_name }
output "listener_arn" { value = aws_lb_listener.http.arn }
output "target_group_arn" { value = aws_lb_target_group.ui.arn }
output "target_ids" { value = { for key, target in aws_lb_target_group_attachment.kind : key => target.target_id } }
