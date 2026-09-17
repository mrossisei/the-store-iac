# ---------------------------------------------------------------------------
# Registry OCI local (equivalente on-premise de ECR/GCR/ACR).
#
# Se publica en 127.0.0.1:5001 para que el host haga `docker push`, y los
# nodos del clúster lo alcanzan por la red bridge como kind-registry:5000.
# containerd, dentro de cada nodo, mapea "localhost:5001" -> kind-registry:5000
# mediante el hosts.toml que montamos en /etc/containerd/certs.d (ver cluster.tf).
# ---------------------------------------------------------------------------
resource "docker_image" "registry" {
  name         = var.registry_image
  keep_locally = true
}

resource "docker_volume" "registry_data" {
  name = "${var.registry_name}-data"

  labels {
    label = "project"
    value = var.project_name
  }
}

resource "docker_container" "registry" {
  name    = var.registry_name
  image   = docker_image.registry.image_id
  restart = "always"

  env = [
    "REGISTRY_STORAGE_DELETE_ENABLED=true",
  ]

  ports {
    internal = 5000
    external = var.registry_host_port
    ip       = "127.0.0.1"
    protocol = "tcp"
  }

  networks_advanced {
    name         = docker_network.kind.name
    ipv4_address = var.registry_ip
  }

  volumes {
    volume_name    = docker_volume.registry_data.name
    container_path = "/var/lib/registry"
  }

  labels {
    label = "project"
    value = var.project_name
  }
}
