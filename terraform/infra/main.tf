# Raíz AWS: red, cómputo, ALB y datos.
locals {
  environment = jsondecode(file("${path.module}/../../config/entorno.json"))
  tools       = jsondecode(file("${path.module}/../../config/herramientas.json"))
  zone_keys   = ["a", "b"]
  zones       = [for key in local.zone_keys : local.environment.zones[key]]
}

module "red" {
  source = "../modules/red"

  name             = local.environment.project
  region           = local.environment.region
  cidr             = local.environment.vpc_cidr
  azs              = local.zones[*].availability_zone
  public_subnets   = local.zones[*].public_cidr
  private_subnets  = local.zones[*].private_cidr
  db_subnets       = local.zones[*].db_cidr
  application_port = local.environment.kind.host_ui_port
}

# El ALB es parte de la red; se instancia aparte porque registra las EC2 y estas
# esperan a la red: un único módulo produciría un ciclo.
module "alb" {
  source = "../modules/red/modules/alb"

  name                  = local.environment.project
  vpc_id                = module.red.vpc_id
  public_subnet_ids     = { for i, key in local.zone_keys : key => module.red.public_subnet_ids[i] }
  alb_security_group_id = module.red.alb_security_group_id
  instance_ids          = module.computo.instance_ids
  application_port      = local.environment.kind.host_ui_port
}

module "computo" {
  source = "../modules/computo"

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

module "datos" {
  source = "../modules/datos"

  name                          = local.environment.project
  vpc_id                        = module.red.vpc_id
  subnet_ids                    = module.red.db_subnet_ids
  application_security_group_id = module.red.application_security_group_id
  db_instance_class             = local.tools.rds_class_candidate
  cache_node_type               = local.tools.cache_node_type
  mysql_engine_version          = local.tools.mysql_engine_version
  postgres_engine_version       = local.tools.postgres_engine_version
  redis_engine_version          = local.tools.redis_engine_version
  availability_zones            = local.zones[*].availability_zone
}
