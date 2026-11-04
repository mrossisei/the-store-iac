mock_provider "aws" {
  mock_resource "aws_lb" {
    defaults = { arn = "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/the-store/50dc6c495c0c9188", dns_name = "the-store.us-east-1.elb.amazonaws.com" }
  }
  mock_resource "aws_lb_target_group" {
    defaults = { arn = "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/the-store-ui/73e2d6bc24d8a067" }
  }
  mock_data "aws_ecr_authorization_token" {
    defaults = { proxy_endpoint = "https://123456789012.dkr.ecr.us-east-1.amazonaws.com", user_name = "AWS", password = "token" }
  }
}
mock_provider "docker" {}
mock_provider "random" {}
mock_provider "kubernetes" {
  alias = "kind_a"
  mock_data "kubernetes_nodes" {
    defaults = { nodes = [] }
  }
}
mock_provider "kubernetes" {
  alias = "kind_b"
  mock_data "kubernetes_nodes" {
    defaults = { nodes = [] }
  }
}

override_data {
  target = data.external.acceso
  values = { result = { kubeconfig_a = "/dev/null", kubeconfig_b = "/dev/null" } }
}

run "pre_entrega" {
  command = apply

  assert {
    condition     = length(module.red.private_subnet_ids) == 2 && length(module.red.db_subnet_ids) == 2
    error_message = "Se requieren subredes privadas y de datos en dos zonas."
  }
  assert {
    condition     = keys(module.computo.instance_ids) == ["a", "b"]
    error_message = "Se requiere una EC2 por zona."
  }
  assert {
    condition     = length(module.imagenes.repositories) == 5
    error_message = "Se requiere un repositorio por microservicio."
  }
}
