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

output "compute" {
  description = "Dos EC2 privadas y sus kind, identificados por a/b; no contiene kubeconfigs."
  value = { for key in local.zone_keys : key => {
    instance_id       = module.computo.instance_ids[key]
    private_ip        = module.computo.private_ips[key]
    availability_zone = local.environment.zones[key].availability_zone
    cluster_name      = local.environment.zones[key].cluster_name
  } }
}

output "url" {
  description = "Entrada HTTP pública del ALB creado por Terraform; la UI se despliega en T08."
  value       = "http://${module.alb.dns_name}"
}

output "load_balancer" {
  description = "Identificadores del ALB/listener/target group y sus EC2 por a/b para verificación."
  value = {
    arn              = module.alb.arn
    dns_name         = module.alb.dns_name
    listener_arn     = module.alb.listener_arn
    target_group_arn = module.alb.target_group_arn
    target_ids       = module.alb.target_ids
  }
}
