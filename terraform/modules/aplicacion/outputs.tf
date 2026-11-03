output "services" { value = keys(local.services) }
output "namespace" { value = kubernetes_namespace_v1.this.metadata[0].name }
output "images" { value = var.images }
output "ui_node_port" { value = var.ui_node_port }
