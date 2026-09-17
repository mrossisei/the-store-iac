# ---------------------------------------------------------------------------
# Capa 2 - Artefactos (imágenes de contenedor)
#
# Construye las imágenes de los cinco microservicios a partir del código
# fuente vendorizado en ../../the-store/src y las publica en el registry local
# creado por la capa 1. El tag de cada imagen es un hash del contenido del
# código fuente del servicio: si el código no cambia, no se reconstruye ni se
# vuelve a publicar nada (build reproducible e idempotente).
# ---------------------------------------------------------------------------
terraform {
  required_version = ">= 1.10.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 4.6"
    }
  }
}
