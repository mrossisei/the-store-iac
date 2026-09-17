# How-to: desplegar The Store con Terraform (kind + Docker)

Guía paso a paso para reproducir el POC del TP Especial de Redes de Información (ITBA, 2C 2026,
tema *Gestión de Infraestructura por Código: Terraform*). Al terminar vas a tener:

- una red Docker propia (`172.30.0.0/24`), un registry OCI local y un clúster Kubernetes 1.35
  de 3 nodos (kind) con ingress-nginx y metrics-server, todo creado por Terraform;
- las 5 imágenes de The Store construidas y publicadas en el registry por Terraform;
- dos entornos de la aplicación, `dev` (in-memory) y `prod` (bases de datos, TLS, HPA,
  NetworkPolicies), accesibles en `http://dev.the-store.localhost` y
  `https://the-store.localhost`.

Tiempo total la primera vez: ~15–20 min (la mayor parte es la compilación de las imágenes Java).
Las siguientes veces, la plataforma completa levanta en ~4 min.

---

## 1. Requisitos

| Requisito | Versión probada | Notas |
|---|---|---|
| Linux x86_64 (probado en Ubuntu 24.04) | — | En macOS/Windows kind funciona, pero `*.localhost` y la red Docker se comportan distinto (ver §8). |
| Docker Engine con BuildKit | 29.7 | El usuario debe pertenecer al grupo `docker`. |
| Terraform | ≥ 1.10 (probado 1.16.3) | `https://developer.hashicorp.com/terraform/install`. OpenTofu ≥ 1.8 también funciona (`tofu` en lugar de `terraform`). |
| kubectl | 1.34–1.36 (política de skew ±1 minor respecto del API server 1.35; probado también con 1.37) | Opcional para Terraform; lo usan los scripts de demo/verificación. |
| make, bash, curl, jq | — | Para el `Makefile` y los scripts. |
| Recursos | 8 vCPU, 12–16 GB RAM, **≥ 15 GB de disco libre** | Imágenes + caché de build + volúmenes de los nodos. |
| Puertos libres en el host | 80, 443 (0.0.0.0), 5001, 6443 (127.0.0.1) | Configurables en `terraform/1-platform/variables.tf`. |

**No hace falta instalar `kind` ni `helm`**: el provider de kind embebe la librería y el provider
de Helm hace lo propio.

Recomendado (kind lo pide para clústeres con muchos pods):

```bash
sudo sysctl fs.inotify.max_user_watches=524288 fs.inotify.max_user_instances=512
```

Verificación automática de todo lo anterior:

```bash
make prereqs
```

---

## 2. Estructura del repositorio

```
the-store-iac/
├── Makefile                  # atajos: make up / down / app ENV=prod / smoke / ...
├── the-store/                # código fuente de The Store (vendorizado; MIT-0)
├── terraform/
│   ├── 1-platform/           # capa 1: red docker, registry, clúster kind, ingress, metrics-server
│   ├── 2-images/             # capa 2: build + push de las imágenes (tag = hash del código)
│   ├── 3-app/                # capa 3: la aplicación; un workspace por entorno (dev, prod)
│   ├── modules/
│   │   ├── microservice/     # Deployment + Service + SA + ConfigMap + HPA/PDB opcionales
│   │   └── datastore/        # StatefulSet + PVC + Secret + Service
│   └── environments/
│       ├── dev.tfvars
│       └── prod.tfvars
├── scripts/                  # check-prereqs, smoke-test, netpol-test, drift-demo, persistence-test
└── docs/                     # pre-entrega, decisiones, presentación, este how-to, diagramas
```

Cada capa tiene su propio estado (`terraform.tfstate`, ignorado por git) y se comunica con la
siguiente mediante `terraform_remote_state`.

---

## 3. Despliegue completo en un comando

```bash
git clone <url-del-repo> the-store-iac
cd the-store-iac
make up
```

`make up` ejecuta, en orden: `make prereqs` → `make platform` → `make images` →
`make app ENV=dev` → `make app ENV=prod` → `make status`.

Al final:

```bash
make status                     # nodos, namespaces, deployments, HPA, NetworkPolicies
export KUBECONFIG=~/.kube/the-store.kubeconfig   # (make kubeconfig lo imprime)
kubectl get pods -A -o wide
```

Abrí `http://dev.the-store.localhost` y `https://the-store.localhost` (certificado autofirmado:
aceptar la advertencia del navegador) o `http://the-store.localhost`.

---

## 4. Paso a paso (lo mismo que hace `make up`, explicado)

### 4.1 Capa 1: plataforma

```bash
cd terraform/1-platform
terraform init
terraform plan            # ~10 recursos: red, volumen, registry, hosts.toml, clúster, 2 releases de Helm, ConfigMap
terraform apply
```

Qué crea (≈ 90 s):

1. `docker_network.kind`: bridge `172.30.0.0/24`, gateway `172.30.0.1`, masquerade activado.
2. `docker_container.registry`: `registry:3` en `172.30.0.100`, publicado en `127.0.0.1:5001`, con volumen persistente.
3. `local_file.registry_hosts_toml`: `.generated/certs.d/localhost:5001/hosts.toml` que se monta en `/etc/containerd/certs.d` de cada nodo (alias `localhost:5001 → kind-registry:5000`).
4. `kind_cluster.this`: 1 control-plane (edge, con puertos 80/443 publicados y label `ingress-ready=true`) + 2 workers; pod CIDR `10.244.0.0/16`, service CIDR `10.96.0.0/16`, API en `127.0.0.1:6443`; kubeconfig en `~/.kube/the-store.kubeconfig`.
5. `helm_release.ingress_nginx` (chart 4.15.1) en el nodo edge con `hostPort`.
6. `helm_release.metrics_server` (chart 3.14.0) para el HPA.
7. `kubernetes_config_map_v1.local_registry_hosting` (KEP-1755) que documenta el registry.

Outputs útiles: `terraform output` (kubeconfig_path, registry_host, docker_network, ingress).

Verificación:

```bash
export KUBECONFIG=~/.kube/the-store.kubeconfig
kubectl get nodes -o wide                          # 3 nodos Ready, IPs 172.30.0.2-4
docker network inspect kind -f '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{"\n"}}{{end}}'
docker exec the-store-worker ip route              # rutas estáticas hacia los /24 de pods de los otros nodos
curl -s http://localhost:5001/v2/_catalog          # registry vacío: {"repositories":[]}
curl -sI http://localhost/                         # 404 de ingress-nginx (todavía no hay Ingress)
```

### 4.2 Capa 2: imágenes

```bash
cd ../2-images
terraform init
terraform apply           # build de ui, catalog, carts, orders, checkout + push (10-15 min la primera vez)
terraform output images   # referencias localhost:5001/the-store-<svc>:<hash>
```

Si volvés a ejecutar `terraform apply` sin cambiar código, el plan es vacío. Si modificás un
archivo de un servicio, cambia su tag y sólo ese servicio se reconstruye y se vuelve a publicar.

Verificación: `curl -s http://localhost:5001/v2/_catalog` lista los 5 repositorios.

### 4.3 Capa 3: aplicación por entorno

```bash
cd ../3-app
terraform init
terraform workspace new dev          # (o: terraform workspace select dev)
terraform apply -var-file=../environments/dev.tfvars     # ~1 min, 22 recursos

terraform workspace new prod
terraform apply -var-file=../environments/prod.tfvars    # ~3 min, ~60 recursos
terraform output                     # url, https_url, datastores, network_policies
```

Con el `Makefile`: `make app ENV=dev`, `make app ENV=prod`, `make plan ENV=prod`, `make outputs ENV=prod`.

---

## 5. Verificación y demos

| Comando | Qué hace | Resultado esperado |
|---|---|---|
| `make smoke ENV=prod` | Flujo de compra con `curl`: home, catálogo (6 productos), detalle, carrito, checkout completo | `13 OK, 0 fallidos` (totales $150 + $10 + $5 = $165) |
| `make netpol-test ENV=prod` | Prueba flujos permitidos y bloqueados por las NetworkPolicies, incluido un pod "intruso" | `14 OK, 0 fallidos` |
| `make persistence-test ENV=prod` | Crea una orden por la API de `orders`, mata el pod (el ReplicaSet lo recrea) y verifica que la orden sigue en PostgreSQL | `✔ la orden sobrevivió al reinicio` |
| `make drift-demo ENV=prod` | `kubectl scale` manual + borrado de un ConfigMap → `terraform plan` detecta ambos → `apply` los corrige | plan con `replicas "3" -> "2"` y `+ create` del ConfigMap |
| `make e2e ENV=prod` | Tests e2e oficiales del proyecto (Cypress en Docker; requiere ~3 GB libres para la imagen `cypress/included`) | `All specs passed!` 13/13 (home 3, catálogo 3, carrito 3, checkout 4) en ~70 s |
| `make load ENV=prod` | Generador de carga (Artillery) 120 s; observar el HPA con `kubectl get hpa -n the-store-prod -w` | réplicas de `ui` suben hasta 4 |

Demo de cambio de configuración con rolling update (tema de la UI):

```bash
cd terraform/3-app && terraform workspace select prod
terraform apply -var-file=../environments/prod.tfvars -var ui_theme=orange   # plan: ConfigMap + template del Deployment
# refrescar https://the-store.localhost -> tema naranja; volver atrás:
terraform apply -var-file=../environments/prod.tfvars
```

Demo de rollback de imagen (tag anterior):

```bash
terraform apply -var-file=../environments/prod.tfvars -var 'images={ui="localhost:5001/the-store-ui:<tag-anterior>"}'
```

Inspección de red útil para la exposición:

```bash
docker network inspect kind | jq '.[0].IPAM.Config'                  # bloque y gateway
docker exec the-store-worker ip route                                 # rutas /24 por nodo (kindnet)
docker exec the-store-control-plane iptables -t nat -L KUBE-SERVICES -n | head   # DNAT de ClusterIP (kube-proxy)
sudo iptables -t nat -S | grep 172.30.0                               # DNAT de puertos y MASQUERADE (Docker)
kubectl -n the-store-prod exec deploy/ui -- cat /etc/resolv.conf     # search domains + CoreDNS 10.96.0.10
kubectl -n the-store-prod get networkpolicy allow-orders -o yaml     # reglas de un workload
kubectl -n the-store-prod exec orders-mq-0 -- rabbitmqctl list_queues  # eventos de órdenes publicados
```

---

## 6. Operación diaria

| Tarea | Comando |
|---|---|
| Ver plan de un entorno | `make plan ENV=prod` |
| Cambiar réplicas/tema/persistencia | editar `terraform/environments/<env>.tfvars` y `make app ENV=<env>` |
| Reconstruir imágenes tras cambiar código | `make images` y luego `make app ENV=<env>` (rolling update automático) |
| Destruir un entorno | `make destroy-app ENV=dev` |
| Destruir todo | `make down` (prod → dev → plataforma; conserva las imágenes locales) o `make down-all` (también la capa 2) |
| Volver a crear todo | `make up` (tras `make down` sólo se vuelven a publicar las imágenes, no se reconstruyen) |
| Formatear/validar | `make fmt` / `make validate` |
| Liberar disco de la caché de build | `docker builder prune` (opcional; la próxima compilación tarda más) |

Un ciclo completo `make down && make up` (con imágenes ya construidas) tarda unos 6 minutos.

---

## 7. Cómo está hecho (mapa rápido del código)

- `terraform/1-platform/network.tf` — la red bridge (CIDR, gateway, masquerade).
- `terraform/1-platform/registry.tf` — registry + volumen + puerto en loopback.
- `terraform/1-platform/cluster.tf` — `kind_cluster` con la topología, los CIDR, los port mappings y el mount de `certs.d`.
- `terraform/1-platform/addons.tf` — ingress-nginx y metrics-server (Helm).
- `terraform/2-images/main.tf` — hash del código fuente, `docker_image` (build) y `docker_registry_image` (push).
- `terraform/3-app/datastores.tf` — 5 instancias del módulo `datastore` (sólo con `persistence = true`).
- `terraform/3-app/services.tf` — 5 instancias del módulo `microservice` con la configuración de cada servicio.
- `terraform/3-app/ingress.tf` — certificado TLS + Secret + Ingress por host.
- `terraform/3-app/network_policies.tf` — tabla de flujos → NetworkPolicies (default-deny + allow).
- `terraform/modules/microservice/main.tf` — el patrón común de los servicios (hardening incluido).
- `terraform/modules/datastore/main.tf` — el patrón común de los datastores.

Las razones detrás de cada decisión están en `docs/decisiones.md`.

---

## 8. Problemas frecuentes

| Síntoma | Causa / solución |
|---|---|
| `make prereqs` dice que el puerto 80 está ocupado | Otro servicio en el host (Apache, nginx, otro kind). Liberarlo o cambiar `http_host_port` en la capa 1. |
| `Error: network with name kind already exists` | Quedó una red `kind` de otro uso. `terraform import docker_network.kind kind` o `docker network rm kind`. |
| `the-store.localhost` no resuelve | Sistemas sin systemd-resolved: agregar `127.0.0.1 the-store.localhost dev.the-store.localhost` en `/etc/hosts`. |
| Pods en `Init:0/1` en prod | Esperan a su base de datos (`wait-for-dependencies`); si persiste, `kubectl describe pod` (imagen de la base no descargada, disco lleno). |
| `too many open files` en pods | Subir los límites de inotify (§1). |
| El apply de la capa 2 falla con `no auth config found for registry` | La capa 1 no está aplicada (el provider lee `registry_host` de su estado). |
| `terraform plan` en la capa 3 falla con "connection refused" | El clúster no existe (capa 1 destruida) o `KUBECONFIG` apunta a otro lado; la capa 3 usa la ruta del estado de la capa 1. |
| Disco lleno durante el build | Cada build de servicio Java usa ~1 GB de caché; `docker builder prune` libera la caché (no borra imágenes). |
| macOS / Windows | Docker Desktop no expone la red `kind` al host: el ingress sigue funcionando (puertos publicados), pero `docker exec ... ip route` y el acceso directo a `172.30.0.x` no. |
| Advertencias `would violate PodSecurity "restricted"` | Son avisos (el namespace *enforce* es `baseline`, *warn* es `restricted`); aparecen con pods lanzados a mano sin securityContext. |

---

## 9. Limpieza total

```bash
make down-all                  # destruye prod, dev, imágenes y plataforma
docker builder prune -f        # opcional: caché de build
docker rmi $(docker images 'localhost:5001/*' -q)   # opcional: imágenes locales
rm -f ~/.kube/the-store.kubeconfig
```

Después de `make down` no queda ningún contenedor, red, volumen ni archivo de kubeconfig creado
por el proyecto (verificable con `docker ps -a`, `docker network ls`, `docker volume ls`).
