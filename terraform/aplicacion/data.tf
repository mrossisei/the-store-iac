# Ambos providers dependen de la misma comprobación: si falla B, tampoco opera A.
# El resultado contiene paths/contextos/UID, nunca CA, certificado ni clave.
data "external" "access" {
  program = ["python3", "${path.module}/../../scripts/validar-acceso.py"]
  query   = { manifest = abspath(var.access_manifest) }
}

data "terraform_remote_state" "infra" {
  count   = var.enable_application ? 1 : 0
  backend = "s3"

  config = {
    bucket       = local.state_bucket
    key          = local.environment.state_keys.infra
    region       = local.environment.region
    encrypt      = true
    use_lockfile = true
  }
}

data "external" "release" {
  count   = var.enable_application ? 1 : 0
  program = ["python3", "${path.module}/../../scripts/seleccionar-release.py"]
  query   = { app_version = var.app_version, manifest = abspath("${path.module}/../imagenes/releases-aplicacion.json") }
}

data "external" "image_cache" {
  count   = var.enable_application ? 1 : 0
  program = ["python3", "${path.module}/../../scripts/preparar-imagenes.py", "check-external"]
  query   = { manifest = abspath(var.access_manifest), images = data.external.release[0].result.images }

  depends_on = [data.external.access]
}
