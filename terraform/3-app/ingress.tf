# ---------------------------------------------------------------------------
# Exposición del entorno: Ingress (L7, name-based virtual hosting) hacia la UI.
# Con tls_enabled se genera un certificado autofirmado "como código".
# ---------------------------------------------------------------------------
resource "tls_private_key" "ingress" {
  count       = var.tls_enabled ? 1 : 0
  algorithm   = "ECDSA"
  ecdsa_curve = "P256"
}

resource "tls_self_signed_cert" "ingress" {
  count           = var.tls_enabled ? 1 : 0
  private_key_pem = tls_private_key.ingress[0].private_key_pem

  subject {
    common_name  = var.hostname
    organization = "The Store - ITBA Redes de Informacion"
  }

  dns_names             = [var.hostname]
  validity_period_hours = 24 * 365
  allowed_uses          = ["key_encipherment", "digital_signature", "server_auth"]
}

resource "kubernetes_secret_v1" "ingress_tls" {
  count = var.tls_enabled ? 1 : 0

  metadata {
    name      = "ui-tls"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = local.common_labels
  }

  type = "kubernetes.io/tls"
  data = {
    "tls.crt" = tls_self_signed_cert.ingress[0].cert_pem
    "tls.key" = tls_private_key.ingress[0].private_key_pem
  }
}

resource "kubernetes_ingress_v1" "ui" {
  metadata {
    name      = "ui"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = local.common_labels
    annotations = {
      # HTTP y HTTPS conviven (sin redirección forzada) para simplificar demos y tests.
      "nginx.ingress.kubernetes.io/ssl-redirect" = "false"
    }
  }

  spec {
    ingress_class_name = "nginx"

    dynamic "tls" {
      for_each = var.tls_enabled ? [1] : []
      content {
        hosts       = [var.hostname]
        secret_name = kubernetes_secret_v1.ingress_tls[0].metadata[0].name
      }
    }

    rule {
      host = var.hostname
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = module.ui.service_host
              port {
                number = 80
              }
            }
          }
        }
      }
    }
  }
}
