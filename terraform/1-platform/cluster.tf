# ---------------------------------------------------------------------------
# Clúster Kubernetes con kind (Kubernetes IN Docker).
#
# Topología: 1 control-plane (que además actúa como nodo "edge": es el único
# con puertos publicados hacia el host y corre el ingress controller) y N
# workers para las cargas de trabajo.
#
# Cada nodo es un contenedor Docker en la red bridge "kind"; adentro corren
# kubelet + containerd (systemd) y los pods reciben IPs del pod_subnet.
# ---------------------------------------------------------------------------
locals {
  certs_dir = "${abspath(path.module)}/.generated/certs.d"

  # Etiqueta que usa ingress-nginx para elegir el nodo edge.
  edge_labels = {
    "ingress-ready"       = "true"
    "the-store.itba/tier" = "edge"
  }
  worker_labels = {
    "the-store.itba/tier" = "workload"
  }
}

# hosts.toml de containerd: alias "localhost:5001" -> http://kind-registry:5000
# (localhost adentro del nodo NO es el host, por eso el alias).
resource "local_file" "registry_hosts_toml" {
  filename        = "${local.certs_dir}/localhost:${var.registry_host_port}/hosts.toml"
  file_permission = "0644"
  content         = <<-EOT
    # Generado por Terraform (capa 1-platform). Alias del registry local.
    [host."http://${var.registry_name}:5000"]
      capabilities = ["pull", "resolve"]
  EOT
}

resource "kind_cluster" "this" {
  name            = var.cluster_name
  node_image      = var.kubernetes_node_image
  wait_for_ready  = true
  kubeconfig_path = pathexpand(var.kubeconfig_path)

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    networking {
      ip_family          = "ipv4"
      api_server_address = "127.0.0.1"
      api_server_port    = var.api_server_port
      pod_subnet         = var.pod_subnet
      service_subnet     = var.service_subnet
      kube_proxy_mode    = "iptables"
    }

    # --- Nodo control-plane / edge ---------------------------------------
    node {
      role   = "control-plane"
      labels = local.edge_labels

      # Port-forwarding (DNAT) host:80/443 -> nodo:80/443, donde escucha
      # ingress-nginx con hostPort.
      extra_port_mappings {
        container_port = 80
        host_port      = var.http_host_port
        protocol       = "TCP"
        listen_address = "0.0.0.0"
      }
      extra_port_mappings {
        container_port = 443
        host_port      = var.https_host_port
        protocol       = "TCP"
        listen_address = "0.0.0.0"
      }

      extra_mounts {
        host_path      = local.certs_dir
        container_path = "/etc/containerd/certs.d"
        read_only      = true
      }
    }

    # --- Nodos worker ----------------------------------------------------
    dynamic "node" {
      for_each = range(var.worker_count)
      content {
        role   = "worker"
        labels = local.worker_labels

        extra_mounts {
          host_path      = local.certs_dir
          container_path = "/etc/containerd/certs.d"
          read_only      = true
        }
      }
    }
  }

  timeouts {
    create = "15m"
    delete = "10m"
  }

  depends_on = [
    docker_network.kind,
    docker_container.registry,
    local_file.registry_hosts_toml,
  ]
}

# KEP-1755: documenta el registry local para herramientas del ecosistema
# (kubectl, skaffold, tilt...) que lo buscan en este ConfigMap.
resource "kubernetes_config_map_v1" "local_registry_hosting" {
  metadata {
    name      = "local-registry-hosting"
    namespace = "kube-public"
  }

  data = {
    "localRegistryHosting.v1" = <<-EOT
      host: "localhost:${var.registry_host_port}"
      hostFromContainerRuntime: "${var.registry_name}:5000"
      hostFromClusterNetwork: "${var.registry_name}:5000"
      help: "https://kind.sigs.k8s.io/docs/user/local-registry/"
    EOT
  }

  depends_on = [kind_cluster.this]
}
