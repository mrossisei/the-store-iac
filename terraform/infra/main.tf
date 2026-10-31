# Raíz AWS independiente del estado histórico EKS: T02 red/SG y T03 cómputo.
# T05/T06 agregan ALB/datos sin requerir providers Kubernetes.
locals {
  environment = jsondecode(file("${path.module}/../../config/entorno.json"))
  zone_keys   = ["a", "b"]
}

module "red" {
  source = "../modules/red"

  name                               = local.environment.project
  region                             = local.environment.region
  cidr                               = local.environment.vpc_cidr
  azs                                = [for key in local.zone_keys : local.environment.zones[key].availability_zone]
  public_subnets                     = [for key in local.zone_keys : local.environment.zones[key].public_cidr]
  private_subnets                    = [for key in local.zone_keys : local.environment.zones[key].private_cidr]
  db_subnets                         = [for key in local.zone_keys : local.environment.zones[key].db_cidr]
  create_application_security_groups = true
  application_port                   = local.environment.kind.host_ui_port
}

locals {
  tools = jsondecode(file("${path.module}/../../config/herramientas.json"))
}

module "computo" {
  source                        = "../modules/computo"
  private_subnet_ids            = { for i, key in local.zone_keys : key => module.red.private_subnet_ids[i] }
  application_security_group_id = module.red.application_security_group_id
  instance_profile_name         = local.environment.iam.instance_profile_name
  ami_id                        = local.tools.ec2_ami_id
  instance_type                 = local.tools.instance_type_candidate
  environment                   = local.environment
  tools                         = local.tools
  # Subred/SG por sí solos no garantizan que NAT/rutas estén listos al arrancar.
  depends_on = [module.red]
}
