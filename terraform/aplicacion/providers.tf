terraform {
  required_version = ">= 1.10"
  required_providers {
    kubernetes = { source = "hashicorp/kubernetes", version = "= 3.4.0" }
    external   = { source = "hashicorp/external", version = "= 2.4.2" }
  }
  backend "s3" {}
}

# Ambos providers dependen de la misma comprobación: si falla B, tampoco opera A.
# El resultado contiene paths/contextos/UID, nunca CA, certificado ni clave.
data "external" "access" {
  program = ["python3", "${path.module}/../../scripts/validar-acceso.py"]
  query   = { manifest = abspath(var.access_manifest) }
}

provider "kubernetes" {
  alias          = "kind_a"
  config_path    = data.external.access.result.kubeconfig_a
  config_context = data.external.access.result.context_a
}

provider "kubernetes" {
  alias          = "kind_b"
  config_path    = data.external.access.result.kubeconfig_b
  config_context = data.external.access.result.context_b
}
