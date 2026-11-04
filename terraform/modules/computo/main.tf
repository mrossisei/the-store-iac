# Una EC2 privada por zona. Al arrancar instala Docker y crea su clúster kind.
locals {
  # Versiones fijadas. Cambiarlas reemplaza las EC2, porque viajan en el user-data.
  tools = {
    kind_version           = "0.33.0"
    kubernetes_version     = "1.37.0"
    kind_node_image        = "kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5"
    calico_manifest_url    = "https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/calico.yaml"
    kind_binary_sha256     = "aee6151561422756b764a4ae28e7f44cda5af5a9eead3cc9985112b1de8d8e0d"
    kubectl_sha256         = "6129359f4e1f3848a5572ccb0b26cf28b8ca08cef38c95a765b2f64a2c961a2f"
    calico_manifest_sha256 = "2de8f47595fb9c41b3f47d7b767a1f8e72ecf84057af834738ff12689a234da5"
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
    config_b64    = base64encode(jsonencode({ cluster_name = "${var.name}-${each.key}", region = var.region, kind = var.kind, tools = local.tools }))
    prepare_b64   = base64gzip(file("${path.module}/prepare.sh"))
    ecr_login_b64 = base64gzip(file("${path.module}/ecr-login.sh"))
  }))

  # Tres saltos: EC2, nodo kind y pod. Cart y Orders usan LabRole desde sus pods.
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
  }

  tags = { Name = "${var.name}-${each.key}" }
}

resource "aws_lb_target_group_attachment" "kind" {
  for_each = aws_instance.kind

  target_group_arn = var.target_group_arn
  target_id        = each.value.id
  port             = var.kind.host_ui_port
}
