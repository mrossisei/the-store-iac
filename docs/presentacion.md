# Guion de la presentación final (30 minutos, remota)

Este documento define qué debe contener la presentación (PPT) y cómo se reparte la demo.
Está pensado para tres oradores (la cátedra exige que **todos** expongan y que **todos** puedan
responder cualquier pregunta). Las respuestas de fondo están en `docs/decisiones.md`.

Reglas de la cátedra a respetar: máximo 30 minutos, demostración funcional obligatoria, exponer
problema → solución → tecnología, presentación online.

---

## 1. Estructura y tiempos sugeridos

| # | Bloque | Min | Orador | Diapositivas |
|---|---|---|---|---|
| 1 | Apertura y contexto: The Store, el `local.sh` imperativo, qué es IaC | 3 | A | 1–4 |
| 2 | Terraform en 5 conceptos: HCL, providers, estado, plan/apply, grafo | 4 | A | 5–8 |
| 3 | Arquitectura del POC: diagrama de red (CIDR, nodos, DMZ, NAT, DNS) | 5 | B | 9–13 |
| 4 | Diseño del código: 3 capas, módulos, entornos, políticas de red | 4 | C | 14–18 |
| 5 | **Demo en vivo** (ver §3) | 10 | B + C | 19 (pantalla compartida) |
| 6 | Lecciones aprendidas, camino a producción (nube), cierre | 3 | A | 20–23 |
| 7 | Preguntas | (resto) | todos | — |

Ensayar con cronómetro: la demo no puede pasar de 10 minutos. Tener **todo levantado de
antemano** (`make up` ejecutado horas antes) y una grabación de respaldo por si falla la
conexión.

---

## 2. Contenido diapositiva por diapositiva

### Bloque 1 · Problema y contexto (A)

1. **Portada**: The Store con Terraform — Redes de Información, ITBA 2C 2026, integrantes.
2. **The Store**: arquitectura de 5 microservicios (ui, catalog, carts, orders, checkout) + sus
   backends (MySQL, DynamoDB, PostgreSQL + RabbitMQ, Redis). Imagen del catálogo.
3. **El problema**: `local.sh` = 400 líneas de bash imperativo: no sabe qué existe, no converge,
   no detecta cambios manuales, no tiene entornos, mezcla build y despliegue. "¿Qué pasa si
   alguien cambió algo con kubectl?" → nadie lo sabe.
4. **Infraestructura como código**: declarativo vs imperativo; idempotencia; versionado; revisión
   por *pull request*; reproducibilidad; el estado como fuente de verdad. Tema asignado: Terraform.

### Bloque 2 · Terraform (A)

5. **Modelo mental**: código HCL (deseado) + estado (conocido) + realidad (providers) →
   `plan` calcula el diff → `apply` lo ejecuta en el orden del grafo de dependencias.
6. **Providers usados** (tabla): docker, kind, helm, kubernetes, random, tls, local; qué recurso
   crea cada uno. Mencionar que el provider de kind embebe la librería (no hace falta el binario).
7. **Estado**: qué contiene, por qué es sensible (contraseñas, clave TLS), *locking*, backends
   remotos (S3/DynamoDB, HCP, `kubernetes`), workspaces.
8. **Terraform vs. alternativas**: Pulumi (mismo modelo, lenguajes generales), OpenTofu (fork MPL,
   compatible), Ansible (configuración, sin plan), Helm/Kustomize (sólo objetos K8s). Por qué
   Terraform (decisión D-01).

### Bloque 3 · Arquitectura y redes (B)

9. **Diagrama general** (`docs/img/arquitectura.svg`) con las 4 capas de direccionamiento:
   LAN 192.168.1.0/24 → red Docker 172.30.0.0/24 → pods 10.244.0.0/16 → services 10.96.0.0/16.
   Insistir: bloques privados (RFC 1918) y **disjuntos**.
10. **La red Docker es un switch + router NAT**: bridge L2 (dominio de broadcast, veth, tabla de
    MACs), gateway 172.30.0.1, SNAT MASQUERADE al salir, DNAT (docker-proxy) al entrar; DNS
    interno por nombre de contenedor. Comando: `docker network inspect kind`, `ip route` en un nodo.
11. **Camino de un request** (norte-sur): navegador → `*.localhost` (RFC 6761) → 127.0.0.1:443
    → DNAT Docker → nodo edge 172.30.0.2:443 → ingress-nginx (L7, `Host:`) → Service `ui`
    (ClusterIP, DNAT de kube-proxy = balanceo L4) → pod `ui`:8080 → backends (este-oeste).
    Cuántos NAT hay en cada sentido (doble/triple NAT del egreso).
12. **Ruteo entre nodos y DNS**: kindnet instala rutas estáticas `/24` por nodo (como `ip route`
    del Lab 5), sin overlay; CoreDNS 10.96.0.10 y `search` del pod; comparar con BGP/Calico
    (por qué no hacía falta).
13. **DMZ y segmentación**: reglas de la DMZ (Clase 6) mapeadas a ingress-nginx + NetworkPolicies:
    Internet→DMZ sólo 80/443; DMZ→interno sólo ui:8080; Internet→interno bloqueado; tabla de
    flujos permitidos = ACL (Clase 4). Aclarar: Kubernetes no aísla por defecto; namespace ≠ VLAN.

### Bloque 4 · Diseño del código (C)

14. **Tres capas, tres estados**: plataforma / imágenes / aplicación; `terraform_remote_state`;
    radio de explosión; la limitación de los providers kubernetes/helm en el mismo módulo del
    clúster.
15. **Módulos**: `microservice` (5 instancias) y `datastore` (5 instancias): qué encapsulan
    (hardening, probes, HPA/PDB, PVC, Secret). Fragmento de `services.tf` mostrando la diferencia
    entre dos servicios (sólo variables).
16. **Entornos**: workspaces `dev`/`prod` + `tfvars`; tabla comparativa (persistencia, réplicas,
    TLS, políticas, HPA). Precondición workspace = environment.
17. **Imágenes como artefactos inmutables**: tag = hash del código; `plan` vacío si no hay
    cambios; rolling update automático; rollback con `-var images=…`; registry local con alias de
    containerd (patrón oficial de kind).
18. **Secretos y TLS como código**: `random_password` → Secret; `tls_self_signed_cert` → Secret
    `kubernetes.io/tls` → Ingress; dónde queda (estado) y qué se haría en producción (Vault,
    cert-manager/ACME).

### Bloque 6 · Cierre (A)

20. **Lecciones aprendidas**: (a) deadlock default-deny vs. initContainers → orden de creación
    de políticas; (b) RabbitMQ 4 rechaza colas transitorias → fijar versiones compatibles con la
    app; (c) provider de Docker y registry HTTP (`registry_auth` + `http://`); (d) HPA vs.
    Terraform por `replicas` (atributo *computed*); (e) disco: caché de BuildKit.
21. **Qué NO hicimos y por qué** (fuera de alcance): nube, observabilidad, CI/CD, mesh (otros
    grupos); IPv6; backend remoto real.
22. **Camino a producción**: mismo código de la capa 3 contra EKS/GKE (cambia la capa 1: VPC con
    subredes públicas/privadas, EKS, RDS/ElastiCache/MQ gestionados, ALB Ingress, ECR, backend S3);
    CI/CD que reemplaza a la capa 2; cert-manager; políticas L7 (mesh).
23. **Cierre**: repo en GitHub (QR), `make up` reproduce todo, agradecimientos.

---

## 3. Guion de la demo (10 minutos, dos ventanas: terminal + navegador)

Preparación (antes de empezar): `make up` completo; `export KUBECONFIG=~/.kube/the-store.kubeconfig`;
terminal con fuente grande; pestañas del navegador abiertas en `https://the-store.localhost` y
`http://dev.the-store.localhost`; `kubectl get hpa -n the-store-prod -w` en una terminal
secundaria si se va a mostrar el HPA.

| Min | Paso | Comando / acción | Qué señalar |
|---|---|---|---|
| 0–1 | Estado inicial | `make status` · `docker ps` · `docker network inspect kind \| jq '.[0].IPAM'` | 3 nodos + registry, IPs 172.30.0.x, dos namespaces |
| 1–2 | La app funciona | navegador: comprar un producto en prod (checkout completo) | Ingress con TLS, `Host:` distinto en dev |
| 2–3 | Idempotencia | `make plan ENV=prod` → "No changes" | Terraform compara deseado vs. estado vs. realidad |
| 3–5 | Drift | `make drift-demo ENV=prod` | `kubectl scale` y borrado de ConfigMap detectados en el plan y corregidos |
| 5–6 | Cambio de configuración | `terraform apply -var ui_theme=orange -var-file=…prod.tfvars` → refrescar navegador | ConfigMap + rolling update sin corte; el plan muestra exactamente qué cambia |
| 6–8 | Segmentación de red | `make netpol-test ENV=prod` | 14 pruebas: flujos permitidos vs. bloqueados; un pod intruso no llega a nada |
| 8–9 | Persistencia y datos | `make persistence-test ENV=prod` · `kubectl exec orders-mq-0 -- rabbitmqctl list_queues` | la orden sobrevive al reinicio; eventos en RabbitMQ |
| 9–10 | Entornos y destroy | `terraform workspace list` · `make destroy-app ENV=dev` (≈20 s) | mismo código, otro tfvars; destroy limpio y acotado (la plataforma sigue) |

Plan B si algo falla en vivo: grabación en video de los mismos pasos (grabar con `asciinema` o
captura de pantalla la semana previa).

---

## 4. Preguntas esperables y quién responde

Cada integrante debe poder responder todas; se sugiere un "dueño" por tema para la primera
respuesta:

- **A (Terraform)**: estado y locking; plan/apply; providers; por qué 3 capas; workspaces;
  secretos en el estado; OpenTofu/licencia; ¿qué pasa si dos aplican a la vez?; ¿cómo importarían
  algo creado a mano? (`terraform import`).
- **B (Redes)**: bloques y máscaras elegidos y qué pasa si se solapan; tipos de NAT (SNAT/DNAT,
  cuántos saltos); bridge = switch L2; ruteo estático entre nodos vs. BGP; DNS (CoreDNS,
  `*.localhost`); L4 (ClusterIP) vs. L7 (ingress); DMZ y sus 4 reglas; ¿por qué no MetalLB/IPv6?
- **C (Kubernetes/app)**: NetworkPolicies (capa en la que filtran, default-deny, deadlock);
  StatefulSet vs. Deployment; PVC/local-path; HPA y `replicas` computed; probes e initContainers;
  hardening de pods (PSA); versiones (RabbitMQ 3.13, MariaDB).

Lista completa de preguntas probables con su respuesta: `docs/decisiones.md` §6 y el resumen
de clases (`docs/resumen-clases.md`).

---

## 5. Material a preparar además de la PPT

- Diagrama de arquitectura en alta resolución (`docs/img/arquitectura.svg` / `.pdf`).
- Capturas de: `terraform plan` con drift, `kubectl get netpol`, `ip route` en un nodo,
  `docker network inspect`, salida de `make smoke`.
- Video de respaldo de la demo (≤ 8 min).
- Enlace al repositorio (GitHub) con el how-to como README visible.
