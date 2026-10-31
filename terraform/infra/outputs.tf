output "network" {
  description = "Contrato de red del camino kind: subredes/NAT/tablas por a-b y SG compartidos."
  value = {
    vpc_id         = module.red.vpc_id
    vpc_cidr       = local.environment.vpc_cidr
    region         = local.environment.region
    public_subnets = { for i, key in local.zone_keys : key => { id = module.red.public_subnet_ids[i], cidr = local.environment.zones[key].public_cidr } }
    private_subnets = { for i, key in local.zone_keys : key => {
      id             = module.red.private_subnet_ids[i]
      cidr           = local.environment.zones[key].private_cidr
      route_table_id = module.red.private_route_table_ids[i]
      nat_public_ip  = module.red.nat_public_ips[i]
    } }
    db_subnets                    = { for i, key in local.zone_keys : key => { id = module.red.db_subnet_ids[i], cidr = local.environment.zones[key].db_cidr } }
    db_route_table_id             = module.red.db_route_table_id
    application_security_group_id = module.red.application_security_group_id
    alb_security_group_id         = module.red.alb_security_group_id
    endpoint_security_group_id    = module.red.endpoint_security_group_id
    gateway_endpoint_ids          = module.red.gateway_endpoint_ids
    sqs_endpoint_id               = module.red.sqs_endpoint_id
  }
}
