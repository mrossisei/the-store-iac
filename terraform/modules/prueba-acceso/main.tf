terraform {
  required_providers {
    kubernetes = { source = "hashicorp/kubernetes", version = "= 3.4.0" }
  }
}

variable "cluster_key" { type = string }
variable "cluster_uid" { type = string }
variable "value" { type = string }

resource "kubernetes_namespace_v1" "probe" {
  metadata {
    name   = "the-store-t04-probe"
    labels = { "app.kubernetes.io/managed-by" = "terraform", "the-store/cluster" = var.cluster_key }
  }
}

resource "kubernetes_config_map_v1" "probe" {
  metadata {
    name      = "access-proof"
    namespace = kubernetes_namespace_v1.probe.metadata[0].name
  }
  data = { cluster = var.cluster_key, cluster_uid = var.cluster_uid, value = var.value }
}
