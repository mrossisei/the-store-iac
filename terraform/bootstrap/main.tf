# ---------------------------------------------------------------------------
# Bootstrap del estado remoto. Se ejecuta UNA sola vez, antes que el resto:
#
#   cd terraform/bootstrap
#   terraform init && terraform apply -var bucket_name=<nombre-unico>
#
# Crea el bucket S3 (con versionado y sin acceso publico) donde el resto de la
# configuracion guarda su estado. Este bootstrap usa estado local: se debe
# conservar en forma privada para administrar el bucket; nunca versionar.
# ---------------------------------------------------------------------------
# Academy deniega GetBucketObjectLockConfiguration, lectura obligatoria del
# recurso aws_s3_bucket en provider 6.66. Se crea/verifica SOLO el bucket con
# CLI y se mantienen cifrado/versionado/policy como recursos Terraform nativos.
# No se necesita Object Lock para el archivo de bloqueo .tflock del backend.
resource "terraform_data" "state_bucket" {
  input            = { bucket = var.bucket_name, region = var.region }
  triggers_replace = [var.bucket_name, var.region]
  lifecycle { prevent_destroy = true }
  provisioner "local-exec" {
    working_dir = "${path.module}/../.."
    command     = "python3 scripts/bootstrap-bucket.py"
    environment = {
      TF_STATE_BUCKET = self.input.bucket
      TF_STATE_REGION = self.input.region
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = terraform_data.state_bucket.output.bucket
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_policy" "tls_only" {
  bucket = terraform_data.state_bucket.output.bucket
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = ["arn:aws:s3:::${var.bucket_name}", "arn:aws:s3:::${var.bucket_name}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = terraform_data.state_bucket.output.bucket

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket = terraform_data.state_bucket.output.bucket

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
