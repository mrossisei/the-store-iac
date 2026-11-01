terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}

locals {
  # Versiones de RDS/Redis y herramientas del operador no son parte del host.
  # Cambiarlas no debe regenerar user-data y reemplazar los dos kind.
  bootstrap_tools = { for key in [
    "kind_version", "kubernetes_version", "kind_node_image", "calico_version",
    "calico_manifest_url", "kind_binary_sha256", "kubectl_sha256", "calico_manifest_sha256",
  ] : key => var.tools[key] }
}

resource "aws_instance" "kind" {
  for_each = var.private_subnet_ids

  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = each.value
  associate_public_ip_address = false
  vpc_security_group_ids      = [var.application_security_group_id]
  iam_instance_profile        = var.instance_profile_name
  user_data_replace_on_change = true
  user_data_base64 = base64gzip(templatefile("${path.module}/cloud-init.yaml.tftpl", {
    config_b64  = base64encode(jsonencode({ environment = var.environment, tools = local.bootstrap_tools, zone = each.key }))
    prepare_b64 = base64gzip(file("${path.module}/prepare.sh"))
    smoke_b64   = base64gzip(file("${path.module}/smoke.sh"))
  }))

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 3
  }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 40
    encrypted             = true
    delete_on_termination = true
    tags                  = { Name = "${var.environment.project}-${each.key}-root" }
  }
  tags = {
    Name    = var.environment.zones[each.key].cluster_name
    Cluster = each.key
  }
}
