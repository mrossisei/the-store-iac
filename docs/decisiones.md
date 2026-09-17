# Registro de decisiones de diseño (ADR) — The Store con Terraform

Este documento registra **todas** las decisiones tomadas para el TP Especial de Redes de
Información (ITBA, 2C 2026, tema *Gestión de Infraestructura por Código: Terraform*), con su
justificación, las alternativas que se evaluaron y por qué se descartaron. Está pensado para que
cualquier integrante del grupo pueda responder "¿por qué hicieron X?" en la defensa oral.

Convención: cada decisión tiene un identificador `D-nn`, y al final hay un índice de preguntas
probables con la decisión que las responde.

---

## 0. Contexto y restricciones que condicionan todo

- **Consigna**: implementar un componente de la arquitectura de *The Store* (tienda online de
  microservicios: `ui` (Java/Spring), `catalog` (Go), `carts` (Java), `orders` (Java),
  `checkout` (Node/NestJS)) y demostrarlo. El tema asignado es IaC con Terraform.
- **La pre-entrega es un contrato**: la cátedra exige implementar *exactamente* lo propuesto. Por
  eso el alcance se definió sobre cosas que **ya probamos que funcionan** antes de escribir la
  pre-entrega, y no sobre deseos.
- **Sin presupuesto cloud**: la cátedra aclara que los costos corren por cuenta del grupo. Un
  clúster EKS + RDS + ElastiCache + MQ cuesta del orden de USD 5–8 por día encendido, más el
  riesgo de olvidarlo prendido. Además, durante la presentación (remota) dependeríamos de
  credenciales, cuotas y latencia hacia la nube.
- **Hardware disponible**: una notebook Linux (Ubuntu 24.04, 8 vCPU, 15 GB RAM, disco casi
  lleno). Esto limitó el tamaño del clúster y obligó a cuidar el consumo de disco de las imágenes.
- **El enunciado provee** un script `local.sh` que despliega The Store en *kind* (Kubernetes in
  Docker) de forma **imperativa** (bash + kubectl apply de un YAML monolítico). Ese script es,
  literalmente, el "problema" que la IaC declarativa viene a resolver.

---

## 1. Decisiones de alcance y plataforma

### D-01 · Terraform (y no Pulumi) como herramienta de IaC

**Decisión**: usar Terraform 1.16 (HCL) con providers `kreuzwerker/docker`, `tehcyx/kind`,
`hashicorp/kubernetes`, `hashicorp/helm`, `hashicorp/random`, `hashicorp/tls`, `hashicorp/local`.

**Por qué**:
- Es el estándar de facto de IaC declarativa: lenguaje HCL específico de dominio, modelo
  *plan → apply* con grafo de dependencias, estado explícito, ecosistema de providers enorme.
- Su modelo declarativo es el que mejor contrasta con `local.sh` (imperativo): con Terraform se
  describe el estado final y la herramienta calcula el *diff*; el script sólo sabe "crear" y
  "borrar", no "converger".
- Tiene detección de *drift* nativa (`terraform plan` compara estado deseado, estado guardado y
  realidad), que es una de las demostraciones centrales del TP.

**Alternativas descartadas**:
- **Pulumi** (el otro nombre del tema): mismo modelo (estado + plan) pero con lenguajes de
  propósito general (TypeScript/Python/Go). Lo descartamos porque (a) HCL es más legible para
  una audiencia mixta y para revisar planes en vivo, (b) Pulumi *Cloud* es el backend por
  defecto (requiere cuenta) y (c) el ecosistema y la documentación de Terraform para
  Kubernetes/Helm/Docker es más madura. Es un reemplazo directo, no una diferencia de fondo.
- **OpenTofu**: fork comunitario (licencia MPL) creado tras el cambio de licencia de Terraform a
  BSL 1.1 en 2023. Es compatible con todo nuestro código (`tofu init/plan/apply`). Elegimos
  Terraform porque es el nombre del tema y el que la industria referencia, pero documentamos que
  el código corre sin cambios en OpenTofu (lo mencionamos en la presentación como nota de
  licencias).
- **Ansible / Helm / Kustomize solos**: Ansible es orientado a configuración, sin estado ni plan
  real (es *push* imperativo idempotente); Helm y Kustomize sólo cubren objetos de Kubernetes, no
  la red Docker, el registry ni el clúster. De hecho **usamos Helm desde Terraform** (D-13) para
  los add-ons, que es la combinación habitual.

### D-02 · Kubernetes local con kind (Kubernetes in Docker) en vez de la nube

**Decisión**: provisionar con Terraform un clúster **kind** dentro de Docker en la notebook,
reproduciendo la topología de un despliegue real (red propia, registry, varios nodos, ingress,
capa de datos), en lugar de un clúster gestionado en AWS/GCP/Azure.

**Por qué**:
- Cero costo, cero dependencia de credenciales o de Internet durante la demo, reproducible
  por cualquier docente en su máquina con `make up`.
- kind es exactamente lo que el enunciado provee (`local.sh` usa kind), así que la comparación
  "antes/después" es directa.
- Todos los conceptos de redes que interesan a la materia están presentes y son inspeccionables:
  bridge L2 de Docker, NAT (SNAT/DNAT), ruteo entre nodos, DNS jerárquico, balanceo L4 y L7,
  segmentación con políticas. En una nube gestionada gran parte de eso queda oculto detrás del
  proveedor.
- El **código no cambia de naturaleza** si se lleva a la nube: los módulos `microservice` y
  `datastore` y la capa 3 funcionan contra cualquier clúster Kubernetes (sólo cambia el
  *provider* que crea el clúster). Lo mostramos en la presentación como "camino a producción".

**Alternativas descartadas**:
- **AWS EKS + RDS + ElastiCache + DynamoDB + Amazon MQ** (la arquitectura de referencia del
  proyecto original de AWS): costo diario, necesidad de cuenta con tarjeta, tiempos de creación
  de 15–20 minutos por apply, y riesgo de que en la presentación remota falle algo externo.
  Además, la cátedra pide precisar CIDR, IPs, SO y protocolos: en EKS gran parte es opaco.
- **minikube / k3d / k3s**: minikube por defecto es una sola VM/contenedor (topología pobre para
  hablar de ruteo entre nodos); k3d es muy similar a kind pero con k3s (Kubernetes recortado,
  Traefik y ServiceLB embebidos que "hacen magia" y esconden lo que queremos mostrar). kind usa
  Kubernetes *vanilla* (kubeadm), tiene provider de Terraform mantenido y es lo que trae el
  enunciado.
- **Docker Compose puro**: no hay Kubernetes, no hay scheduler ni Services ni políticas de red;
  perderíamos toda la capa que interesa.

### D-03 · kind provisionado *desde* Terraform con el provider `tehcyx/kind`

**Decisión**: el clúster es un recurso Terraform (`kind_cluster`) y no un prerrequisito creado a
mano. El provider embebe la librería de kind (v0.31), así que **no hace falta instalar el binario
`kind`**.

**Por qué**: la gracia del TP es que *todo* (red, registry, clúster, add-ons, imágenes, app) se
cree y destruya con `terraform apply/destroy`; si el clúster se creara fuera de Terraform no
podríamos hablar de idempotencia ni de destroy completo.

**Alternativa descartada**: `null_resource` + `local-exec` ejecutando `kind create cluster`.
Funciona, pero es imperativo, no tiene *read* (Terraform no puede detectar si el clúster
existe) y complica el destroy. Lo mismo vale para invocar `local.sh` desde Terraform.

### D-04 · Tres capas (root modules) con estados independientes

**Decisión**: separar el código en tres *root modules* con su propio `terraform.tfstate`:

| Capa | Directorio | Provisiona | Frecuencia de cambio |
|---|---|---|---|
| 1 Plataforma | `terraform/1-platform` | red Docker, registry, clúster kind, ingress-nginx, metrics-server | muy baja |
| 2 Artefactos | `terraform/2-images` | build + push de las 5 imágenes | cada cambio de código |
| 3 Aplicación | `terraform/3-app` | namespaces, datos, microservicios, ingress, políticas; un *workspace* por entorno | alta |

Las capas se comunican con `terraform_remote_state` (la capa 3 lee `kubeconfig_path` y las
referencias de imágenes de las capas 1 y 2).

**Por qué**:
- **Radio de explosión** (*blast radius*): un `destroy` o un error en la capa 3 no puede
  tocar el clúster; un cambio de réplicas no obliga a Terraform a refrescar la red Docker.
- **Limitación documentada de los providers kubernetes/helm**: HashiCorp desaconseja crear el
  clúster y usar sus credenciales para recursos Kubernetes *en el mismo módulo* (los recursos
  que necesitan hablar con la API durante el `plan`, como `kubernetes_manifest`, fallan si el
  clúster todavía no existe). En la capa 1 sólo usamos `helm_release` y `kubernetes_config_map_v1`,
  que toleran credenciales desconocidas en el plan; todo lo demás va en la capa 3, donde el
  clúster ya existe.
- **Ciclo de vida distinto**: la plataforma cambia una vez; las imágenes cambian con cada commit;
  la app cambia varias veces por día. Mezclarlos en un estado obliga a planes largos y a bloquear
  el estado completo por cambios chicos.
- **Permisos** (en un equipo real): quien despliega la app no necesita permisos para borrar el
  clúster.

**Alternativas descartadas**:
- **Un solo root module**: más simple de explicar, pero cae en la limitación anterior y un
  `terraform destroy` accidental borra todo. Además, los `docker_image` de las imágenes
  quedarían atados al mismo estado que el clúster.
- **Terragrunt**: resuelve la orquestación de capas (dependencias, DRY de backends) pero agrega
  una herramienta más; con tres capas y un `Makefile` alcanza.
- **Una capa por microservicio**: sobre-ingeniería para cinco servicios que se despliegan
  siempre juntos.

### D-05 · Entornos `dev` y `prod` con *workspaces* + archivos `tfvars`

**Decisión**: la capa 3 usa un **workspace de Terraform por entorno** (estado separado
`terraform.tfstate.d/<env>`) y un archivo `environments/<env>.tfvars` con los parámetros del
entorno. Ambos entornos conviven en el mismo clúster, cada uno en su namespace
(`the-store-dev`, `the-store-prod`) y con su propio host de ingress
(`dev.the-store.localhost`, `the-store.localhost`).

| Parámetro | dev | prod |
|---|---|---|
| persistencia | in-memory | MariaDB, PostgreSQL, Redis, RabbitMQ, DynamoDB Local |
| réplicas ui / catalog | 1 / 1 | 2 / 2 (+ HPA en ui 2–4) |
| NetworkPolicies | no | sí (default-deny + allow explícito) |
| TLS en el ingress | no | sí (certificado autofirmado generado por Terraform) |

**Por qué**: es la demostración más clara de "mismo código, distinta configuración": el
`terraform plan` con `prod.tfvars` muestra 40+ recursos más que con `dev.tfvars` sin tocar un
`.tf`. Un workspace por entorno evita que el estado de `dev` y `prod` se pisen (cada uno tiene
su lock y su historial). Una **precondición** en el namespace verifica que el workspace activo
coincida con `var.environment` para evitar aplicar `prod.tfvars` en el workspace `dev`.

**Alternativas descartadas**:
- **Dos clústeres kind (uno por entorno)**: es lo "correcto" en producción (aislamiento total),
  pero duplica RAM/disco (imposible en la notebook) y el enunciado no lo requiere. Lo explicamos
  como el siguiente paso: la capa 1 admite `cluster_name` y puertos distintos, así que sería
  aplicar la capa 1 dos veces con otros tfvars.
- **Un directorio por entorno (`envs/dev`, `envs/prod`) que instancian un módulo común**: es el
  patrón recomendado por HashiCorp para entornos con *backends* distintos. Con backend local y
  dos entornos, los workspaces son más simples y la demo (`terraform workspace select prod`) es
  más didáctica. Ambos patrones se explican en la presentación.
- **Namespaces como "VLANs"**: no lo son. Un namespace es una frontera administrativa (RBAC,
  cuotas, nombres), no de red: sin NetworkPolicies, un pod de `dev` alcanza a uno de `prod`.
  Por eso el aislamiento de red se implementa aparte (D-17).

---

## 2. Decisiones de red

### D-06 · Bloque 172.30.0.0/24 para la red Docker `kind` (creada por Terraform)

**Decisión**: Terraform crea la red *bridge* de Docker llamada `kind` con subred
**172.30.0.0/24**, gateway **172.30.0.1** (la interfaz `br-*` del host). Los nodos reciben IPs
dinámicas por IPAM de Docker (`.2`, `.3`, `.4`) y el registry tiene la IP fija **172.30.0.100**.

**Por qué**:
- kind, si encuentra una red Docker llamada `kind`, la **reutiliza** en vez de crear la suya
  (que por defecto sería un /16 elegido por Docker, típicamente 172.18.0.0/16). Crearla nosotros
  nos da control del bloque, del gateway y de las opciones (masquerade) y lo deja documentado
  en código.
- 172.30.0.0/24 es un bloque privado (172.16.0.0/12, RFC 1918) que **no se solapa** con: la LAN
  del host (192.168.1.0/24), el resto de redes Docker de la máquina (172.17–172.23.0.0/16), el
  pod CIDR (10.244.0.0/16) ni el service CIDR (10.96.0.0/16). El solapamiento es el error
  clásico: el kernel no sabría por qué interfaz enviar un paquete.
- Un /24 (254 hosts) sobra para 3 nodos + registry y deja margen para más workers. Elegimos
  /24 y no /16 por el principio de "reservar sólo lo necesario y alineado" que se practica en
  los ejercicios de VLSM del Lab 1; si hiciera falta un pool de IPs para un LoadBalancer
  (MetalLB) se ampliaría el bloque en la variable `docker_network_subnet`.
- La red bridge de Docker es, en términos de la materia, **un switch L2 (un dominio de
  broadcast)** con un router NAT pegado: cada contenedor se conecta por un par `veth`, el bridge
  aprende MACs y reenvía tramas, y `iptables MASQUERADE` hace **SNAT** al salir por la
  interfaz del host.

**Alternativas descartadas**:
- Dejar que kind cree la red con su bloque por defecto: no reproducible (Docker elige el
  siguiente /16 libre) y no documentado como código.
- Usar `KIND_EXPERIMENTAL_DOCKER_NETWORK` para una red con otro nombre: depende de una variable
  de entorno del proceso de Terraform (frágil e invisible en el código).
- Bloques 10.x: se reservan para pods y services para que las tres capas de direccionamiento
  se distingan a simple vista (172.30 = nodos, 10.244 = pods, 10.96 = services).

### D-07 · Pod CIDR 10.244.0.0/16 y Service CIDR 10.96.0.0/16

**Decisión**: `pod_subnet = 10.244.0.0/16` (cada nodo recibe un /24: control-plane
10.244.0.0/24, workers 10.244.1.0/24 y 10.244.2.0/24) y `service_subnet = 10.96.0.0/16`
(ClusterIPs; `kubernetes` = 10.96.0.1, CoreDNS = 10.96.0.10). Ambos explícitos en el código.

**Por qué**:
- 10.244.0.0/16 es el bloque que usan kindnet y Flannel por convención: 256 subredes /24 → hasta
  256 nodos con 254 pods cada uno, sobra para el POC y es reconocible por cualquiera que haya
  visto un clúster.
- Para services usamos /16 (65 534 IPs virtuales) en lugar del /12 por defecto de kind
  (10.96.0.0/12 = 1 M de IPs): mismo criterio de no reservar de más. Sigue conteniendo las IPs
  "conocidas" 10.96.0.1 y 10.96.0.10.
- Las ClusterIP **no existen en ninguna interfaz**: son IPs virtuales que `kube-proxy` (modo
  iptables) resuelve con reglas de **DNAT** hacia las IPs de pods; es un balanceo L4 por
  conexión. Por eso el service CIDR no necesita ruta: lo consume iptables en cada nodo.

**Alternativa descartada**: reutilizar los valores por defecto sin escribirlos. Preferimos que
el diagrama y el código digan lo mismo y que un cambio de bloque sea un cambio de variable.

### D-08 · CNI kindnet (por defecto) con ruteo estático entre nodos, sin overlay

**Decisión**: mantener **kindnet**, el CNI por defecto de kind. No instalamos Calico ni Cilium.

**Por qué**:
- kindnet instala en cada nodo **rutas estáticas** hacia el /24 de pods de los demás nodos
  (`10.244.1.0/24 via 172.30.0.4`), exactamente el `ip route <red> <máscara> <next-hop>` del
  Lab 5. Como los tres nodos comparten el mismo bridge L2, el tráfico pod-a-pod entre nodos
  viaja **sin encapsular** (no hay VXLAN ni IPIP, no hay overhead de MTU): el nodo origen
  reenvía el paquete con IP de pod al nodo destino por su MAC. Se comprueba con `ip route`
  dentro de un nodo.
- Desde kind v0.24, kindnet implementa **NetworkPolicy** mediante `kube-network-policies`, así
  que no hace falta otro CNI para segmentar (D-17). Lo verificamos empíricamente con
  `scripts/netpol-test.sh`.
- Menos componentes = menos RAM/disco y menos riesgo en la demo.

**Alternativas descartadas**:
- **Calico**: habría permitido mostrar **BGP** (cada nodo como peer iBGP anunciando su /24,
  como en el Lab 6) o VXLAN. Es muy atractivo para la materia, pero agrega ~10 pods, 300 MB de
  imágenes, un operador y dependencias del kernel; y con todos los nodos en el mismo segmento
  L2, BGP no aporta nada funcional frente a las rutas estáticas. Queda documentado como
  extensión: en un clúster multi-subred (nodos en distintas L2) sería obligatorio ruteo
  dinámico o encapsulación.
- **Cilium**: eBPF, muy potente, pero ídem en complejidad y más lejos del contenido de la materia.

### D-09 · Exposición por Ingress (L7) con hostPort + port mapping de kind; sin LoadBalancer

**Decisión**: el nodo control-plane actúa como **nodo edge**: kind publica `0.0.0.0:80→80` y
`0.0.0.0:443→443` del host hacia ese contenedor (**DNAT de Docker**), e ingress-nginx corre
allí con `hostPort` (nodeSelector `ingress-ready=true`, tolerando el taint del control-plane).
El ingress enruta por **nombre de host** (`Host:` HTTP) a la UI de cada entorno.

Cadena completa de un request desde el navegador:
`127.0.0.1:80 (host)` →DNAT docker→ `172.30.0.2:80 (nodo edge)` →hostPort→ `pod ingress-nginx`
→proxy L7 por Host→ `Service ui (ClusterIP 10.96.x.x:80)` →DNAT kube-proxy→ `pod ui 10.244.x.x:8080`.

**Por qué**:
- Es el patrón documentado por kind para ingress y reproduce el rol de **DMZ** de la Clase 6:
  Internet→DMZ controlado (sólo 80/443), DMZ→interno mínimo (sólo el Service `ui`, forzado
  por NetworkPolicy), Internet→interno bloqueado (ningún microservicio publica puertos).
- Name-based virtual hosting permite dos entornos con la misma IP y puerto.
- `*.localhost` resuelve a loopback por RFC 6761 en systemd-resolved y en los navegadores, así
  que no hay que editar `/etc/hosts`.

**Alternativas descartadas**:
- **MetalLB (L2/ARP) + Service LoadBalancer**: funciona en Linux con kind (el host llega a la red
  172.30.0.0/24 directamente), y sería un buen gancho con ARP. Pero no funciona en macOS/Windows
  (la red Docker no es alcanzable desde el host), agrega un componente y no aporta nada a la
  demo que el hostPort no dé. Se menciona como alternativa en la presentación.
- **NodePort**: obligaría a usar puertos 30000–32767 en la URL y no permitiría virtual hosting
  sin ingress.
- **`kubectl port-forward`**: imperativo y efímero; no es infraestructura.

### D-10 · Registry OCI local con alias `localhost:5001` (patrón oficial de kind)

**Decisión**: un contenedor `registry:3` (`kind-registry`, 172.30.0.100, publicado sólo en
`127.0.0.1:5001`) conectado a la red `kind`. Los nodos lo alcanzan como `kind-registry:5000`
por el DNS interno de Docker. En cada nodo, containerd recibe un `hosts.toml` (montado por
Terraform vía `extraMounts`) que hace que `localhost:5001` sea alias de
`http://kind-registry:5000`. Así, la **misma referencia de imagen** (`localhost:5001/the-store-ui:tag`)
sirve para `docker push` desde el host y para el `image:` del pod.

**Por qué**:
- Es el equivalente local de ECR/GCR: la app se despliega **por referencia a un registry**, no
  cargando tarballs en cada nodo. Los nodos hacen *pull* sólo de lo que ejecutan.
- "localhost adentro del nodo no es el host" (cada contenedor tiene su propio loopback); el alias
  resuelve esa asimetría de forma declarativa, sin `docker exec` imperativos.
- El registry se publica **sólo en loopback** del host para no exponerlo en la LAN.

**Alternativas descartadas**:
- **`kind load docker-image`** (lo que hace `local.sh`): copia la imagen a *todos* los nodos
  (3 copias), es imperativo y se pierde al recrear el clúster. El provider tiene un recurso
  `kind_load` en desarrollo pero no está en la versión publicada.
- **Docker Hub / GHCR**: exigen cuenta, subir imágenes públicas y depender de Internet en la demo.

### D-11 · TLS autofirmado generado por Terraform en `prod`

**Decisión**: en `prod`, Terraform genera una clave ECDSA P-256 y un certificado autofirmado
(`tls_self_signed_cert`) para `the-store.localhost`, lo guarda en un Secret `kubernetes.io/tls`
y lo referencia desde el Ingress (HTTPS en 443; HTTP sigue disponible, sin redirección forzada).

**Por qué**: muestra que hasta el material criptográfico puede ser código (con la salvedad de
que la clave privada queda en el estado, ver D-19). En producción real se reemplaza por
cert-manager + ACME (Let's Encrypt), que se menciona como evolución. No forzamos la redirección
HTTP→HTTPS para que los tests y la demo con `curl` no dependan de `-k`.

### D-12 · Ruteo desde el host y resolución de nombres

**Decisión**: no tocar `/etc/hosts` ni el DNS del host; usar `*.localhost`.

**Por qué**: systemd-resolved (Ubuntu) responde `::1`/`127.0.0.1` para cualquier `*.localhost`
(RFC 6761) y Chrome/Firefox hacen lo mismo internamente. Documentamos el fallback (`/etc/hosts`)
en el how-to para otros sistemas. Dentro del clúster, CoreDNS (10.96.0.10) resuelve
`<svc>.<ns>.svc.cluster.local`; los pods usan nombres cortos (`http://catalog`) porque el
`search` de su `/etc/resolv.conf` incluye el namespace.

---

## 3. Decisiones de plataforma Kubernetes

### D-13 · Add-ons con Helm desde Terraform (ingress-nginx 4.15.1, metrics-server 3.14.0)

**Decisión**: `helm_release` con versiones fijadas y valores en `yamlencode`, no manifiestos
YAML descargados por URL.

**Por qué**: Helm es el formato de distribución de estos componentes; fijar la versión del chart
hace el despliegue reproducible (el `local.sh` original descarga "la última" de una URL). El
provider de Helm devuelve el estado del release y permite `terraform destroy` limpio.
metrics-server es necesario para el HPA y `kubectl top` y en kind requiere
`--kubelet-insecure-tls` (los kubelets usan certificados autofirmados).

### D-14 · Topología 1 control-plane + 2 workers; Kubernetes 1.35 fijado por digest

**Decisión**: tres nodos (el control-plane también es edge de ingress; los workers corren app y
datos), imagen `kindest/node:v1.35.0@sha256:…` fijada por digest.

**Por qué**: con 2 workers hay ruteo real entre nodos (pods en 10.244.1.0/24 y 10.244.2.0/24),
distribución de réplicas y un `PodDisruptionBudget` con sentido; más nodos no agregan concepto y
sí RAM/disco. Fijar la imagen por digest (y no `latest`) es lo que garantiza que dentro de dos
meses la demo levante lo mismo. La versión 1.35 es la que trae la librería kind embebida en el
provider; la máquina de desarrollo tiene `kubectl` 1.37 (compatibilidad ±1 minor de la API es
suficiente para administración).

### D-15 · Módulos reutilizables `microservice` y `datastore`

**Decisión**: dos módulos propios en `terraform/modules`. `microservice` (ServiceAccount +
ConfigMap + Deployment + Service + HPA/PDB opcionales) se instancia 5 veces; `datastore`
(Secret + Service + StatefulSet con PVC) se instancia 5 veces en `prod`.

**Por qué**: los cinco servicios comparten el 90 % del manifiesto (`dist/kubernetes.yaml` tiene
5 copias casi idénticas de 60 líneas). Con módulos, el *hardening* (usuario 1000 no root, root
filesystem de sólo lectura, `drop ALL` capabilities, seccomp `RuntimeDefault`, `/tmp` en
memoria), los probes y los labels estándar (`app.kubernetes.io/*`) se escriben una vez y se
prueban una vez. Mostrarlo es responder "¿qué aporta Terraform sobre el YAML?": abstracción y
reutilización con variables tipadas y validadas.

**Alternativas descartadas**:
- **`kubernetes_manifest` con el YAML original**: reutiliza el manifiesto pero pierde tipado,
  validación en plan y la posibilidad de parametrizar; además `kubernetes_manifest` necesita el
  clúster durante el plan.
- **Un chart de Helm propio + `helm_release`**: válido (es lo que hace el proyecto original de
  AWS), pero movería la lógica a templates Go fuera de Terraform y la demo de *drift* sería
  menos directa (Helm no detecta cambios hechos con kubectl).

### D-16 · Capa de datos real en `prod` (StatefulSets) y decisiones por motor

**Decisión**: en `prod` cada servicio usa el backend previsto por The Store, desplegado en el
clúster como StatefulSet con volumen persistente (StorageClass `standard`, local-path
provisioner de kind), credenciales generadas por `random_password` en Secrets:

| Servicio | Backend | Imagen | Puerto | Por qué esa imagen |
|---|---|---|---|---|
| catalog | MySQL-compatible | `mariadb:11.4` | 3306/TCP | el `docker-compose` upstream usa MariaDB; 330 MB vs 600 MB de `mysql:8` |
| orders | PostgreSQL | `postgres:17-alpine` | 5432/TCP | imagen oficial, mínima |
| orders (eventos) | RabbitMQ (AMQP 0-9-1) | `rabbitmq:3.13-management-alpine` | 5672 + 15672 | versión con la que se desarrolló la app (ver nota); consola de administración útil para la demo |
| checkout | Redis (RESP) | `redis:7-alpine` (AOF) | 6379/TCP | mínima; `appendonly` para persistir |
| carts | DynamoDB API | `amazon/dynamodb-local` | 8000/HTTP | único emulador de la API que usa el SDK del servicio |

**Por qué**: es lo que diferencia `prod` de `dev` y lo que permite demostrar persistencia
(`scripts/persistence-test.sh`: se crea una orden, se reinicia el pod de `orders`, la orden
sigue). Los StatefulSets dan identidad estable (`orders-db-0`) y PVC propio.

**Nota sobre la versión de RabbitMQ (hallazgo de las pruebas)**: con `rabbitmq:4` el checkout
devolvía HTTP 500. El servicio `orders` declara su cola como *transitoria y no exclusiva*
(`new Queue("orders-orders-queue", durable=false)`), y RabbitMQ 4.x rechaza esa combinación por
la deprecación `transient_nonexcl_queues` (error AMQP 541 `INTERNAL_ERROR`). La orden igual se
guardaba en PostgreSQL (la publicación del evento ocurre después del *commit*), pero el
servicio respondía error. Se fijó `rabbitmq:3.13`, la línea que usa el `docker-compose`
original (`rabbitmq:3-management`). Moraleja para el oral: la infraestructura debe fijarse a las
versiones con las que la aplicación fue probada; "latest" no es una versión.

**Alternativas descartadas**:
- **Charts de Bitnami**: hasta 2025 eran el estándar; Broadcom restringió el catálogo gratuito
  (imágenes movidas a `bitnamilegacy` sin actualizaciones). Preferimos imágenes oficiales y un
  módulo propio simple.
- **Bases de datos como contenedores Docker fuera del clúster** (emulando RDS "afuera"):
  interesante como analogía, pero obliga a que los pods salgan de la red del clúster y a
  gestionar dos mundos de red; en Kubernetes lo normal para un POC es dentro del clúster.
- **Operadores (CloudNativePG, etc.)**: sobredimensionado para el alcance.

### D-17 · Segmentación de red con NetworkPolicies (modelo *default-deny*)

**Decisión**: en `prod`, en el namespace de la app:
1. `default-deny-all` (ingress + egress) para todos los pods;
2. `allow-dns-egress` hacia CoreDNS (kube-system, 53/UDP y TCP);
3. `allow-ingress-controller-to-ui` (sólo desde el namespace `ingress-nginx`, puerto 8080);
4. una política `allow-<servicio>` por workload generada con `for_each` a partir de una **tabla
   de flujos** (`from → to : puerto`), que actúa como lista de reglas de firewall (ACL):
   `ui→{catalog,carts,orders,checkout}:8080`, `checkout→orders:8080`,
   `catalog→catalog-db:3306`, `orders→orders-db:5432`, `orders→orders-mq:5672`,
   `checkout→checkout-redis:6379`, `carts→carts-db:8000`.

**Por qué**:
- Kubernetes **no aísla nada por defecto** (red plana): cualquier pod habla con cualquier pod,
  incluso entre namespaces. Es la "trampa" habitual y la razón de este punto.
- Es la traducción directa del modelo DMZ/ACL de la Clase 6/4: una NetworkPolicy filtra en
  **L3/L4** (selector de pods/namespaces ≈ IPs, puerto y protocolo); no mira HTTP.
- La tabla de flujos es dato, no código: agregar un microservicio es agregar una fila. Terraform
  la convierte en objetos y `plan` muestra exactamente qué reglas cambian.

**Lección aprendida (importante para el oral)**: en la primera versión, las políticas
`allow-*` tenían `depends_on` a los Deployments. Resultado: la denegación por defecto se aplicó
al instante, los `initContainers` de espera no pudieron conectarse a las bases y Terraform quedó
esperando el rollout: **deadlock por orden de creación**. La corrección fue que las políticas
dependan sólo del namespace, para que existan antes que los pods. En un firewall físico es el
mismo principio: nunca aplicar "deny all" antes de las reglas de permiso.

**Alternativas descartadas**: separar la capa de datos en otro namespace (agrega
`namespaceSelector` sin cambiar el concepto); Calico/Cilium para políticas L7 (fuera de alcance).

### D-18 · Autoscaling (HPA) en `prod` y quién es dueño de `replicas`

**Decisión**: HPA v2 sobre `ui` (2–4 réplicas, 70 % de CPU). En el módulo, el Deployment fija
`replicas` **sólo cuando no hay HPA**; con HPA el atributo se deja sin definir
(`replicas = var.autoscaling != null ? null : var.replicas`).

**Por qué**: si Terraform y el HPA "pelean" por `replicas`, cada `apply` desharía el
autoscaling. En el provider de Kubernetes `spec.replicas` es *Optional + Computed*: si no se
declara, Terraform acepta el valor que haya en el clúster y no lo considera drift; si se declara,
lo impone. Así `ui` queda gobernada por el HPA y el resto por Terraform, sin duplicar recursos.

**Alternativa descartada**: `lifecycle { ignore_changes = [spec[0].replicas] }` en todos los
Deployments (nuestra primera versión). Funciona para el HPA, pero como `lifecycle` es estático
(no admite condiciones) también ocultaba el drift de réplicas en los servicios sin HPA: la demo
de `kubectl scale catalog --replicas=3` no aparecía en el plan. Se detectó en las pruebas y se
cambió al enfoque *computed*. Por eso la demo de drift (D-21) usa `catalog` y no `ui`. También
agregamos `PodDisruptionBudget` (`minAvailable: 1`) cuando hay más de una réplica o HPA.

---

## 4. Decisiones sobre estado, secretos y ciclo de vida

### D-19 · Backend local para el estado (con la discusión de backends remotos)

**Decisión**: estado en archivos locales (`terraform.tfstate` por capa y por workspace),
excluidos del repositorio.

**Por qué**: es un POC en una sola máquina; el backend local ya provee **locking** (archivo
`.terraform.tfstate.lock.info`) y serialización. Para un equipo real se usaría un backend
remoto con locking (S3 + DynamoDB o S3 con `use_lockfile`, Terraform Cloud/HCP, GCS, un
`kubernetes` backend que guarda el estado en un Secret del clúster). Lo explicamos en la
presentación con el ejemplo de dos personas aplicando a la vez.

**Consecuencia sobre secretos**: el estado contiene en claro las contraseñas generadas
(`random_password`) y la clave TLS. Por eso: (a) el estado no se versiona, (b) los outputs
sensibles están marcados `sensitive`, (c) en producción el backend remoto debe cifrar en reposo y
restringir acceso, o usar un gestor externo (Vault, AWS Secrets Manager) y referenciarlo con
`data sources`/`ephemeral` values.

### D-20 · Imágenes construidas por Terraform con tag = hash del código fuente

**Decisión**: la capa 2 construye cada imagen con `docker_image { build {} }` y la publica con
`docker_registry_image`. El tag es `substr(sha1(hashes de todos los archivos fuente), 0, 12)`.

**Por qué**:
- Idempotencia real: si el código no cambió, `plan` no muestra nada; si cambió un archivo, el
  tag cambia, se reconstruye sólo ese servicio y la capa 3 hace un *rolling update* porque
  cambia la referencia de imagen (artefactos inmutables, nada de `latest`).
- Permite la demo "cambio de código → apply → nueva versión en producción" en un solo comando y
  permite **rollback** pasando un tag anterior con `-var 'images={...}'`.

**Trade-offs discutidos**: construir imágenes es tarea de CI/CD (otro tema del TP), no de IaC;
lo dejamos en una capa separada justamente para poder reemplazarla por un pipeline que haga
`docker push` y publique los tags. Un aspecto práctico: el provider construye con BuildKit
igual que `docker build`, así que la caché de build ocupa disco; el how-to documenta
`docker builder prune` como limpieza opcional.

**Detalles no obvios que costaron tiempo** (útiles si preguntan "qué problemas tuvieron"):
- El provider de Docker exige un bloque `registry_auth` aun para un registry sin autenticación
  (`auth_disabled = true`), y para consultar el digest por HTTP plano hay que declarar la
  dirección con prefijo `http://` (si no, asume HTTPS y falla contra el registry local).
- Terraform trata a `docker_image.service` como un solo recurso con 5 instancias; un
  `-target` sobre una instancia de `docker_registry_image` arrastra el build de todas.

### D-21 · Estrategia de demostración de *drift* y de cambios

**Decisión**: `scripts/drift-demo.sh` escala `catalog` a mano con `kubectl` y borra un ConfigMap;
`terraform plan` muestra ambas desviaciones y `apply` las corrige. Para cambios "de negocio" se
usa `ui_theme` (default → orange): el plan muestra el cambio en el ConfigMap y en la anotación
del pod template, y el apply hace un rolling update visible en el navegador.

**Por qué**: son las dos capacidades que un script bash no tiene (comparar realidad vs. deseado y
converger con cambios mínimos) y se ven en menos de dos minutos, apto para 30 minutos de
presentación.

### D-22 · Pruebas: smoke test propio + tests e2e oficiales opcionales

**Decisión**: `scripts/smoke-test.sh` reproduce con `curl` el flujo de los tests Cypress del
proyecto (home, catálogo de 6 productos, detalle "The Quiet Quill", agregar al carrito,
checkout completo con totales $150 + $10 + $5 = $165). Los tests e2e oficiales quedan
disponibles con `make e2e` (imagen `cypress/included`, ~2,5 GB).

**Por qué**: el smoke test corre en segundos, sin descargar 2,5 GB, y valida lo mismo de punta
a punta (ui→catalog/carts/checkout→orders→PostgreSQL/RabbitMQ). Los e2e oficiales se
mantienen para la validación final y para mostrar equivalencia con `local.sh e2e-test`.

### D-23 · Vendorizar el código de The Store dentro del repositorio

**Decisión**: el repo contiene una copia del código fuente (`the-store/`) en lugar de un
submódulo o de asumir un checkout aparte.

**Por qué**: la capa 2 necesita el contexto de build y el hash del código; con la copia, el
repositorio es autocontenido y el hash es determinista para cualquiera que lo clone. La licencia
del proyecto (MIT-0) lo permite.

### D-24 · Versiones fijadas de todo

Terraform `>= 1.10`, providers con `~>` (parche libre, minor fija) y `.terraform.lock.hcl`
versionado; charts con `version`; imagen de nodo por digest; imágenes de datos por tag mayor.
**Por qué**: reproducibilidad entre la pre-entrega (septiembre) y la defensa (noviembre).

---

## 5. Cosas que evaluamos y dejamos fuera de alcance (con motivo)

| Idea | Motivo de exclusión |
|---|---|
| Observabilidad (Prometheus/Grafana), logs centralizados, service mesh, WAF, CI/CD | Son temas de **otros grupos**; sólo dejamos los puntos de integración (labels, metrics-server, capa 2 reemplazable por CI). |
| Chat con GenAI de la UI | No tiene relación con IaC; se deja deshabilitado (`RETAIL_UI_CHAT_ENABLED` por defecto `false`). |
| IPv6 / dual-stack | kind lo soporta, pero duplicaría CIDRs y reglas sin cambiar conceptos; se explica como extensión. |
| Backend remoto real (S3/HCP) | Requiere cuenta; se explica en la presentación. |
| Terraform `test` (`.tftest.hcl`) | Valioso, pero el tiempo se priorizó en pruebas de integración reales (smoke, netpol, persistencia, drift). Queda como mejora sugerida. |

---

## 6. Índice de preguntas probables → decisión que las responde

| Pregunta | Ver |
|---|---|
| ¿Por qué Terraform y no Pulumi/Ansible/Helm? ¿Y OpenTofu? | D-01 |
| ¿Por qué no lo hicieron en AWS? ¿Cómo se llevaría a la nube? | D-02, D-04 |
| ¿Por qué tres estados? ¿Qué pasa si destruyo la capa 3? | D-04 |
| ¿Cómo manejan entornos? ¿Namespaces = VLANs? | D-05, D-17 |
| ¿Por qué esos bloques? ¿Qué pasa si se solapan con mi Wi-Fi? | D-06, D-07 |
| ¿Qué es la red Docker en términos de capa 2? ¿Dónde está el NAT? ¿De qué tipo? | D-06, D-09 |
| ¿Cómo llega un paquete del navegador al pod? ¿Cuántos DNAT hay? | D-09 |
| ¿Ruteo estático o dinámico entre nodos? ¿Overlay? ¿BGP? | D-08 |
| ¿Dónde está la DMZ? ¿Qué está permitido en cada dirección? | D-09, D-17 |
| ¿Kubernetes aísla pods por defecto? ¿En qué capa filtra una NetworkPolicy? | D-17 |
| ¿Cómo resuelve nombres un pod? ¿Y el navegador con `*.localhost`? | D-12 |
| ¿Qué pasa si dos personas hacen apply a la vez? ¿Dónde están los secretos? | D-19 |
| ¿Qué pasa si alguien cambia algo con kubectl? | D-21, D-18 |
| ¿Cómo versionan las imágenes? ¿Cómo hacen rollback? | D-20 |
| ¿Qué problemas tuvieron? | D-17 (deadlock), D-16 (RabbitMQ 4), D-18 (HPA vs. replicas), D-20 (registry_auth/http), disco (§0) |
| ¿Por qué kind y no minikube/k3d? | D-02 |
| ¿Cómo probaron que funciona? | D-22 y `docs/how-to.md` §Verificación |
