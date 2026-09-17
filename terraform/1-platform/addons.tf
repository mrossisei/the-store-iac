# ---------------------------------------------------------------------------
# Add-ons de plataforma instalados con Helm.
# ---------------------------------------------------------------------------

# ingress-nginx: reverse proxy L7 (HTTP/HTTPS) en el nodo edge. Usa hostPort
# para escuchar directamente en los puertos 80/443 del nodo, que kind mapea a
# los puertos del host (no hay LoadBalancer en un clúster local).
resource "helm_release" "ingress_nginx" {
  name             = "ingress-nginx"
  namespace        = "ingress-nginx"
  create_namespace = true
  repository       = "https://kubernetes.github.io/ingress-nginx"
  chart            = "ingress-nginx"
  version          = var.ingress_nginx_chart_version

  wait    = true
  timeout = 600

  values = [yamlencode({
    controller = {
      replicaCount = 1
      hostPort     = { enabled = true }
      service      = { type = "ClusterIP" }
      nodeSelector = { "ingress-ready" = "true" }
      tolerations = [{
        key      = "node-role.kubernetes.io/control-plane"
        operator = "Equal"
        effect   = "NoSchedule"
      }]
      updateStrategy = {
        type          = "RollingUpdate"
        rollingUpdate = { maxUnavailable = 1 }
      }
      publishService           = { enabled = false }
      extraArgs                = { "publish-status-address" = "localhost" }
      watchIngressWithoutClass = true
      ingressClassResource     = { default = true }
      config = {
        # Loguea la IP real del cliente aunque venga por el docker-proxy.
        "use-forwarded-headers" = "true"
      }
    }
  })]

  depends_on = [kind_cluster.this]
}

# metrics-server: provee la Metrics API (CPU/memoria de pods y nodos) que
# consume el HorizontalPodAutoscaler. En kind los kubelets usan certificados
# autofirmados, por eso --kubelet-insecure-tls.
resource "helm_release" "metrics_server" {
  count = var.enable_metrics_server ? 1 : 0

  name       = "metrics-server"
  namespace  = "kube-system"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  version    = var.metrics_server_chart_version

  wait    = true
  timeout = 300

  values = [yamlencode({
    args = ["--kubelet-insecure-tls"]
  })]

  depends_on = [kind_cluster.this]
}
