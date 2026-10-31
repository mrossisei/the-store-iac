# Nueva raíz AWS independiente del estado histórico EKS. T02 crea solo red/SG.
# T03/T05/T06 agregan cómputo, ALB y datos sin requerir providers Kubernetes.
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
