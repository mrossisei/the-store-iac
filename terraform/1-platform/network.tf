# ---------------------------------------------------------------------------
# Red bridge de Docker: es el "switch L2 + router NAT" donde se conectan los
# nodos del clúster (contenedores) y el registry.
#
#  - Docker crea una interfaz bridge en el host (br-<id>) con la IP gateway.
#  - Cada contenedor se conecta con un par veth y recibe una IP del CIDR.
#  - El tráfico hacia afuera se enmascara (SNAT/MASQUERADE) con la IP del host.
#  - Docker provee DNS interno: los contenedores se resuelven por nombre.
# ---------------------------------------------------------------------------
resource "docker_network" "kind" {
  name   = var.docker_network_name
  driver = "bridge"

  ipam_config {
    subnet  = var.docker_network_subnet
    gateway = var.docker_network_gateway
  }

  options = {
    "com.docker.network.bridge.enable_ip_masquerade" = "true"
  }

  labels {
    label = "project"
    value = var.project_name
  }
  labels {
    label = "managed-by"
    value = "terraform"
  }
}
