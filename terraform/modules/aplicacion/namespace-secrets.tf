resource "kubernetes_namespace_v1" "this" {
  metadata {
    name   = var.namespace
    labels = { project = "the-store" }
  }
}
resource "kubernetes_secret_v1" "databases" {
  metadata {
    name      = "databases"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
  }
  data = {
    mysql_password    = var.databases.mysql_password
    postgres_password = var.databases.postgres_password
  }
  type = "Opaque"
}
