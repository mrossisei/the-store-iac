# Guion de la presentación final

Máximo 30 minutos, remota, con demostración funcional obligatoria. Los tres integrantes tienen
que exponer y cualquiera puede recibir preguntas sobre cualquier parte.

---

## Estructura y tiempos

| Bloque | Min | Orador | Contenido |
|---|---|---|---|
| 1. Problema | 3 | A | Qué es The Store, qué hace `local.sh` y qué le falta |
| 2. Qué es IaC y Terraform | 4 | A | Declarativo vs imperativo, estado, plan/apply, providers |
| 3. Arquitectura | 6 | B | El diagrama: bloques de direcciones, nodos, camino del tráfico, segmentación |
| 4. El código | 4 | C | Los cuatro módulos, las variables, cómo se lee un plan |
| 5. Demo en vivo | 10 | B y C | Los cuatro casos de uso |
| 6. Cierre | 3 | A | Limitaciones, camino a producción, conclusiones |

## Diapositivas sugeridas

1. **Portada.** Título, materia, integrantes.
2. **The Store.** Los cinco microservicios y sus bases de datos. Captura de la tienda.
3. **El problema.** `local.sh`: 300 líneas de bash imperativo. No sabe qué existe, no converge,
   no detecta cambios manuales, no se puede parametrizar.
4. **Infraestructura como Código.** Declarativo vs imperativo. Qué aporta: reproducibilidad,
   versionado, revisión por *plan*, detección de drift.
5. **Terraform en una lámina.** Código + estado + realidad → plan → apply. Providers usados.
6. **Arquitectura (diagrama).** Los tres bloques de direcciones, los tres nodos, el camino de un
   pedido desde el navegador hasta la base de datos.
7. **Redes en detalle.** Por qué esos bloques y por qué no se solapan; los dos saltos de NAT; el
   Ingress como balanceador de capa 7 frente al Service de capa 4; el DNS interno.
8. **Segmentación.** Las cuatro NetworkPolicies y el paralelo con los *security groups* y con la
   idea de DMZ.
9. **El código.** Estructura de módulos y `terraform.tfvars` en pantalla.
10. **Demo.** (pantalla compartida)
11. **Limitaciones y camino a producción.** Estado local vs remoto, credenciales, la carga de
    imágenes con `local-exec`, migración a la nube.
12. **Conclusiones.**

## Demo (10 minutos)

Antes de empezar: entorno levantado, `export KUBECONFIG=~/.kube/the-store.kubeconfig`, terminal
con letra grande, el navegador abierto en `http://the-store.localhost`. Tener grabado un video
de respaldo.

| Min | Qué se muestra | Comando |
|---|---|---|
| 0-1 | La tienda funciona: se compra un producto | navegador |
| 1-2 | Qué hay detrás | `kubectl get pods -n the-store -o wide` · `docker network inspect kind` |
| 2-3 | Idempotencia | `terraform plan` → "No changes" |
| 3-5 | **Caso 1: drift.** Alguien escala a mano y Terraform lo detecta y corrige | `kubectl scale deploy/catalog --replicas=5` → `terraform plan` → `terraform apply` |
| 5-6 | **Caso 2: escalar.** Se cambia una línea de `terraform.tfvars` | `ui = 4` → `terraform apply` |
| 6-8 | **Caso 3: nueva versión y rollback.** | `app_version = "1.1"` → `apply` → volver a `"1.0"` → `apply` |
| 8-9 | **Caso 4: segmentación de red.** Un pod ajeno no llega a la base | `./verificar.sh` |
| 9-10 | Destrucción y recreación | `terraform destroy` (mostrar el plan, no ejecutarlo entero) |

## Preguntas esperables

Todas están respondidas en `docs/decisiones.md`. Reparto sugerido de la primera respuesta:

- **A (Terraform):** qué es el estado y dónde vive; qué pasa si dos personas aplican a la vez;
  diferencia con Ansible y con Helm; por qué no Pulumi; qué hace `terraform import`.
- **B (Redes):** por qué esos bloques y qué pasa si se solapan; dónde está el NAT y de qué tipo;
  qué es la red de Docker en términos de capa 2; cómo llega un pedido del navegador al pod;
  balanceo de capa 4 vs capa 7; cómo resuelve nombres un pod; en qué capa filtra una
  NetworkPolicy.
- **C (Kubernetes y aplicación):** diferencia entre Deployment y StatefulSet; qué pasa si se
  cae un pod; dónde se guardan los datos y las credenciales; cómo se actualiza una versión sin
  cortar el servicio; por qué Kubernetes no aísla la red por defecto.

## Material a preparar

- Diagrama en alta resolución (`docs/img/arquitectura.pdf`).
- Capturas de: un `terraform plan` con drift, `kubectl get pods -o wide`, la salida de
  `./verificar.sh`.
- Video de respaldo de la demo (máximo 8 minutos).
- Enlace al repositorio.
