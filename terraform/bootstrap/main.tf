# ---------------------------------------------------------------------------
# Bootstrap del estado remoto. Se ejecuta UNA sola vez, antes que el resto:
#
#   cd terraform/bootstrap
#   terraform init && terraform apply -var bucket_name=<nombre-unico>
#
# Crea el bucket S3 (con versionado y sin acceso publico) donde el resto de la
# configuracion guarda su estado. Este bootstrap usa estado local, que no hace
# falta versionar: el bucket se puede reconocer por su nombre.
# ---------------------------------------------------------------------------
terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  description = "Region donde se crea el bucket (la misma que el resto del proyecto)."
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Nombre del bucket de estado. Debe ser unico en todo AWS (ej: the-store-tfstate-<apellido>)."
  type        = string
}

resource "aws_s3_bucket" "state" {
  bucket = var.bucket_name

  tags = { Project = "the-store", ManagedBy = "terraform" }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_name" {
  description = "Poner este nombre en terraform/backend.tf."
  value       = aws_s3_bucket.state.bucket
}
