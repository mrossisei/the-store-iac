# The Store × Terraform — Infraestructura como Código

**Redes de Información · ITBA · 2C 2026 · TP Especial · Tema 1: Gestión de Infraestructura por Código (Terraform)**

Este repositorio contiene la implementación completa del TP: **toda** la infraestructura
necesaria para correr la tienda de microservicios *The Store* —red, registry de imágenes,
clúster Kubernetes (kind), ingress, capa de datos, microservicios, TLS y políticas de red—
descripta en Terraform, organizada en capas y entornos, con scripts de verificación y demos.

```
make up          # red 172.30.0.0/24 + registry + kind (3 nodos) + ingress + imágenes + entornos dev y prod
make smoke ENV=prod
make down
```

| Documento | Contenido |
|---|---|
| [`docs/guia-terraform-para-el-grupo.md`](docs/guia-terraform-para-el-grupo.md) | **Empezá por acá si nunca usaste Terraform**: conceptos, cómo leer HCL, orden de lectura del repo, ejercicios, qué es The Store, Kubernetes mínimo, IDE. |
| [`docs/how-to.md`](docs/how-to.md) | **Guía paso a paso** (requisitos, despliegue, verificación, operación, problemas frecuentes). |
| [`docs/preentrega.pdf`](docs/preentrega.pdf) | Documento de **pre-entrega** (problemática, diseño, alcance y casos de uso, diagrama de arquitectura con CIDR/IP/SO/protocolos, alternativas). Fuente: `docs/preentrega.tex`. |
| [`docs/decisiones.md`](docs/decisiones.md) | **Registro de decisiones** (D-01…D-24): qué se eligió, por qué, qué alternativas se descartaron y qué problemas aparecieron. |
| [`docs/presentacion.md`](docs/presentacion.md) | Guion de la **presentación final** (estructura de la PPT, tiempos, demo de 10 minutos, preguntas esperables). |
| [`docs/img/arquitectura.svg`](docs/img/arquitectura.svg) | Diagrama de arquitectura (también en `.png` y `.pdf`). |
| [`docs/resumen-clases.md`](docs/resumen-clases.md) | Resumen del material de la cátedra y su relación con el TP (para preparar el oral). |

## Arquitectura en una imagen

![Arquitectura](docs/img/arquitectura.png)

## Estructura

```
terraform/1-platform   capa 1: red Docker, registry OCI, clúster kind (K8s 1.35), ingress-nginx, metrics-server
terraform/2-images     capa 2: build + push de las 5 imágenes (tag = hash del código fuente)
terraform/3-app        capa 3: la aplicación; workspaces dev / prod con environments/<env>.tfvars
terraform/modules      módulos reutilizables: microservice, datastore
scripts/               check-prereqs, smoke-test, netpol-test, persistence-test, drift-demo
the-store/             código fuente de The Store (vendorizado, licencia MIT-0)
```

## Qué demuestra

1. **Provisionamiento desde cero** con un comando y **destrucción completa** sin residuos.
2. **Idempotencia** (segundo `plan` vacío) y **cambios controlados** (rolling update de un cambio de configuración).
3. **Detección y corrección de drift** (cambios manuales con `kubectl` revertidos por `terraform apply`).
4. **Entornos** `dev` (in-memory) y `prod` (MariaDB, PostgreSQL, RabbitMQ, Redis, DynamoDB Local, TLS, HPA) con el mismo código.
5. **Segmentación de red como código**: NetworkPolicies *default-deny* + tabla de flujos, verificadas automáticamente.
6. **Persistencia** de órdenes y **autoscaling** de la UI.

## Licencias

El código de *The Store* pertenece a sus autores (fork del *retail-store-sample-app* de AWS,
licencia MIT-0). El código Terraform y la documentación de este repositorio son parte del TP
Especial de Redes de Información (ITBA).
