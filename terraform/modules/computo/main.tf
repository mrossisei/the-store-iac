terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
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
    config_b64  = base64encode(jsonencode({ environment = var.environment, tools = var.tools, zone = each.key }))
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
