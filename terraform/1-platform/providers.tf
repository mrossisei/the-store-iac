# El provider de Docker habla con el daemon local por el socket Unix.
provider "docker" {
  host = var.docker_host
}

# El provider de kind embebe la librería de kind (sigs.k8s.io/kind), por lo
# que NO hace falta tener el binario `kind` instalado.
provider "kind" {}

# helm y kubernetes se configuran con las credenciales que devuelve el
# recurso kind_cluster. Esto crea una dependencia "provider -> recurso" dentro
# de la misma capa, que Terraform tolera porque estos providers difieren la
# configuración hasta el apply (ver docs/decisiones.md, decisión D-04).
provider "helm" {
  kubernetes = {
    host                   = kind_cluster.this.endpoint
    client_certificate     = kind_cluster.this.client_certificate
    client_key             = kind_cluster.this.client_key
    cluster_ca_certificate = kind_cluster.this.cluster_ca_certificate
  }
}

provider "kubernetes" {
  host                   = kind_cluster.this.endpoint
  client_certificate     = kind_cluster.this.client_certificate
  client_key             = kind_cluster.this.client_key
  cluster_ca_certificate = kind_cluster.this.cluster_ca_certificate
}
