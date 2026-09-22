# ---------------------------------------------------------------------------
# Red del cluster.
#
# Es una red "bridge" de Docker: funciona como un switch de capa 2 al que se
# conectan los nodos del cluster, con un gateway que hace NAT hacia Internet.
# Cumple el mismo rol que una VPC con su subred en un proveedor de nube.
#
# El nombre debe ser "kind": la herramienta que crea el cluster busca una red
# con ese nombre y, si existe, la reutiliza en lugar de crear una propia. Asi
# somos nosotros los que definimos el bloque de direcciones.
# ---------------------------------------------------------------------------

terraform {
  required_providers {
    docker = { source = "kreuzwerker/docker" }
  }
}

resource "docker_network" "this" {
  name   = var.network_name
  driver = "bridge"

  ipam_config {
    subnet  = var.subnet
    gateway = cidrhost(var.subnet, 1)
  }
}
