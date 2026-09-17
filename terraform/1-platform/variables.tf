# ----------------------------- Generales -----------------------------------
variable "project_name" {
  description = "Nombre del proyecto; se usa como prefijo/etiqueta de todos los recursos."
  type        = string
  default     = "the-store"
}

variable "docker_host" {
  description = "Endpoint del daemon de Docker."
  type        = string
  default     = "unix:///var/run/docker.sock"
}

# ----------------------------- Red Docker ----------------------------------
variable "docker_network_name" {
  description = <<-EOT
    Nombre de la red bridge de Docker donde viven los nodos del clúster y el
    registry. Debe llamarse "kind": la librería de kind busca una red con ese
    nombre y, si existe, la reutiliza en lugar de crear la suya (así somos
    nosotros quienes definimos el bloque CIDR).
  EOT
  type        = string
  default     = "kind"
}

variable "docker_network_subnet" {
  description = "Bloque CIDR (RFC 1918) de la red bridge de los nodos. No debe solaparse con la LAN del host ni con los CIDR de pods/servicios."
  type        = string
  default     = "172.30.0.0/24"

  validation {
    condition     = can(cidrnetmask(var.docker_network_subnet))
    error_message = "docker_network_subnet debe ser un bloque CIDR IPv4 válido, por ejemplo 172.30.0.0/24."
  }
}

variable "docker_network_gateway" {
  description = "IP del gateway de la red bridge (es la IP de la interfaz br-* del host)."
  type        = string
  default     = "172.30.0.1"
}

# ----------------------------- Registry ------------------------------------
variable "registry_name" {
  description = "Nombre del contenedor del registry OCI local. Los nodos lo resuelven por DNS de Docker con este nombre."
  type        = string
  default     = "kind-registry"
}

variable "registry_ip" {
  description = "IP estática del registry dentro de la red bridge."
  type        = string
  default     = "172.30.0.100"
}

variable "registry_host_port" {
  description = "Puerto en loopback del host (127.0.0.1) donde se publica el registry para hacer `docker push`."
  type        = number
  default     = 5001
}

variable "registry_image" {
  description = "Imagen del registry OCI (Distribution)."
  type        = string
  default     = "registry:3"
}

# ----------------------------- Clúster -------------------------------------
variable "cluster_name" {
  description = "Nombre del clúster kind. El contexto de kubeconfig se llama kind-<cluster_name>."
  type        = string
  default     = "the-store"
}

variable "kubernetes_node_image" {
  description = "Imagen de nodo de kind, fijada por digest para reproducibilidad (Kubernetes v1.35.0, kind v0.31.0)."
  type        = string
  default     = "kindest/node:v1.35.0@sha256:452d707d4862f52530247495d180205e029056831160e22870e37e3f6c1ac31f"
}

variable "worker_count" {
  description = "Cantidad de nodos worker (además del control-plane)."
  type        = number
  default     = 2

  validation {
    condition     = var.worker_count >= 1 && var.worker_count <= 5
    error_message = "worker_count debe estar entre 1 y 5."
  }
}

variable "pod_subnet" {
  description = "CIDR para las IPs de los pods (cada nodo recibe un /24 de este bloque)."
  type        = string
  default     = "10.244.0.0/16"
}

variable "service_subnet" {
  description = "CIDR para las ClusterIP de los Services (IPs virtuales que implementa kube-proxy con DNAT)."
  type        = string
  default     = "10.96.0.0/16"
}

variable "api_server_port" {
  description = "Puerto en 127.0.0.1 del host donde se publica el API server (HTTPS)."
  type        = number
  default     = 6443
}

variable "http_host_port" {
  description = "Puerto del host que se mapea al puerto 80 del nodo edge (ingress HTTP)."
  type        = number
  default     = 80
}

variable "https_host_port" {
  description = "Puerto del host que se mapea al puerto 443 del nodo edge (ingress HTTPS)."
  type        = number
  default     = 443
}

variable "kubeconfig_path" {
  description = "Ruta donde kind escribe el kubeconfig del clúster (no se toca ~/.kube/config)."
  type        = string
  default     = "~/.kube/the-store.kubeconfig"
}

# ----------------------------- Add-ons -------------------------------------
variable "ingress_nginx_chart_version" {
  description = "Versión del chart de ingress-nginx."
  type        = string
  default     = "4.15.1"
}

variable "enable_metrics_server" {
  description = "Instala metrics-server (necesario para HPA / kubectl top)."
  type        = bool
  default     = true
}

variable "metrics_server_chart_version" {
  description = "Versión del chart de metrics-server."
  type        = string
  default     = "3.14.0"
}
