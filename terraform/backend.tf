# ---------------------------------------------------------------------------
# Estado remoto: el archivo de estado se guarda en un bucket S3 con versionado
# y bloqueo nativo (use_lockfile), para que los tres integrantes trabajen sobre
# el mismo entorno sin pisarse. El bucket se crea una sola vez con la
# configuracion de bootstrap/ (ver README).
#
# El nombre del bucket es unico a nivel global: reemplazar el valor por el
# elegido en bootstrap/terraform.tfvars.
# ---------------------------------------------------------------------------
terraform {
  backend "s3" {
    bucket       = "the-store-tfstate-CAMBIAR"
    key          = "the-store/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }
}
