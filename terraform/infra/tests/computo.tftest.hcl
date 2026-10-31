mock_provider "aws" {}

run "dos_hosts_privados" {
  command = apply
  module { source = "../modules/computo" }
  variables {
    private_subnet_ids            = { a = "subnet-00000000000000001", b = "subnet-00000000000000002" }
    application_security_group_id = "sg-00000000000000001"
    instance_profile_name         = "LabInstanceProfile"
    ami_id                        = "ami-0c230065b91270bc6"
    instance_type                 = "t3.large"
    environment                   = jsondecode(file("../../config/entorno.json"))
    tools                         = jsondecode(file("../../config/herramientas.json"))
  }
  assert {
    condition     = keys(aws_instance.kind) == ["a", "b"] && aws_instance.kind["a"].subnet_id == "subnet-00000000000000001" && aws_instance.kind["b"].subnet_id == "subnet-00000000000000002"
    error_message = "Debe existir exactamente una EC2 por subred privada."
  }
  assert {
    condition     = alltrue([for i in aws_instance.kind : !i.associate_public_ip_address && i.iam_instance_profile == "LabInstanceProfile" && i.vpc_security_group_ids == toset(["sg-00000000000000001"])])
    error_message = "EC2 sin IP pública y con perfil existente/SG de aplicación."
  }
  assert {
    condition     = alltrue([for i in aws_instance.kind : one(i.metadata_options).http_tokens == "required" && one(i.metadata_options).http_put_response_hop_limit == 3])
    error_message = "IMDSv2 obligatorio con saltos explícitos; verificar pods en T08."
  }
  assert {
    condition     = alltrue([for i in aws_instance.kind : one(i.root_block_device).encrypted && one(i.root_block_device).delete_on_termination && one(i.root_block_device).volume_size == 40 && i.user_data_replace_on_change && length(i.user_data_base64) < 21840])
    error_message = "Disco cifrado con eliminación y bootstrap comprimido dentro del límite EC2."
  }
  assert {
    condition     = keys(output.instance_ids) == ["a", "b"] && keys(output.private_ips) == ["a", "b"]
    error_message = "Outputs mantienen el contrato por a/b."
  }
}
