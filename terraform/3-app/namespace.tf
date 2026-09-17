resource "kubernetes_namespace_v1" "this" {
  metadata {
    name = local.namespace
    labels = merge(local.common_labels, {
      # Pod Security Admission: baseline obligatorio, restricted como aviso.
      "pod-security.kubernetes.io/enforce" = "baseline"
      "pod-security.kubernetes.io/warn"    = "restricted"
    })
  }

  lifecycle {
    precondition {
      condition     = terraform.workspace == var.environment
      error_message = "El workspace activo (${terraform.workspace}) no coincide con var.environment (${var.environment}). Ejecutá: terraform workspace select ${var.environment}"
    }
  }
}
