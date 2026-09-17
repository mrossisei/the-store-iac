# Guía para el grupo: Terraform desde cero, leyendo este repositorio

Esta guía es para quien nunca usó Terraform (ni Kubernetes) y tiene que entender, defender y
poder modificar este TP. Está pensada para leerse con el repo abierto al lado. Tiempo estimado:
una tarde para la parte 1 a 4; la parte 5 (ejercicios) se hace con el clúster levantado.

Índice: 1) Qué es Terraform · 2) Vocabulario · 3) Cómo se lee HCL · 4) El ciclo de trabajo ·
5) Mapa del repo y orden de lectura · 6) Ejercicios · 7) Qué es The Store y qué nos importa ·
8) Kubernetes mínimo · 9) IDE y herramientas · 10) Referencias

---

## 1. Qué es Terraform (en diez líneas)

Terraform es una herramienta de **Infraestructura como Código** (IaC). En lugar de crear cosas a
mano (clics en una consola, comandos `docker run`, `kubectl apply`, scripts bash), escribís en
archivos de texto **cómo querés que quede** la infraestructura: "quiero una red con este bloque
de IPs, un clúster con 3 nodos, un deployment con 2 réplicas de la imagen X". Eso se llama
enfoque **declarativo**: describís el *estado deseado*, no los pasos.

Terraform lee esos archivos, se fija qué existe realmente (a través de los **providers**, que son
plugins que hablan con la API de Docker, Kubernetes, AWS, etc.), guarda lo que creó en un
archivo de **estado**, y calcula un **plan**: la diferencia entre lo que hay y lo que querés.
Después ejecuta ese plan (**apply**) creando, modificando o borrando sólo lo necesario, en el
orden correcto (arma un grafo de dependencias). Si corrés `apply` dos veces sin cambiar nada,
la segunda no hace nada: eso es **idempotencia**. Si alguien cambió algo a mano, el próximo
`plan` lo muestra: eso es **detección de drift**.

En este TP, Terraform reemplaza al script `the-store/local.sh` (400 líneas de bash imperativo)
por unos 40 archivos `.tf` que describen red, registry, clúster, imágenes y aplicación.

## 2. Vocabulario (lo que vas a ver en cada archivo)

| Término | Qué es | Ejemplo en el repo |
|---|---|---|
| **Provider** | Plugin que sabe hablar con una API. Se declara en `required_providers` y se configura en un bloque `provider`. | `docker` (habla con el daemon de Docker), `kind` (crea el clúster), `kubernetes`, `helm`. Ver `terraform/1-platform/providers.tf`. |
| **Resource** | Un objeto que Terraform crea y administra. Sintaxis `resource "tipo" "nombre" { ... }`. | `resource "docker_network" "kind"` en `1-platform/network.tf`. |
| **Data source** | Algo que Terraform sólo *lee* (no crea). Sintaxis `data "tipo" "nombre"`. | `data "terraform_remote_state" "platform"` en `3-app/providers.tf` lee los outputs de la capa 1. |
| **Variable** (`var.x`) | Un parámetro de entrada, con tipo, descripción y valor por defecto. | `variable "worker_count"` en `1-platform/variables.tf`. |
| **tfvars** | Archivo con valores para las variables. Es lo que cambia entre entornos. | `terraform/environments/dev.tfvars` y `prod.tfvars`. |
| **Local** (`local.x`) | Un valor calculado dentro del código, para no repetir. | `locals { namespace = "the-store-${local.env}" }` en `3-app/locals.tf`. |
| **Output** | Un valor que el módulo expone hacia afuera (a la terminal o a otra capa). | `output "kubeconfig_path"` en `1-platform/outputs.tf`. |
| **Module** | Un directorio de `.tf` reutilizable, que se invoca con `module "nombre" { source = "..." }` pasándole variables. | `terraform/modules/microservice` se instancia 5 veces en `3-app/services.tf`. |
| **Root module** | El directorio donde ejecutás `terraform`. Tiene su propio estado. | `1-platform`, `2-images`, `3-app` (tres estados independientes). |
| **State** (`terraform.tfstate`) | Archivo JSON con lo que Terraform creó y sus IDs reales. Es la "memoria" de Terraform. No se versiona en git (tiene contraseñas). | `terraform/3-app/terraform.tfstate.d/prod/terraform.tfstate`. |
| **Backend** | Dónde se guarda el estado. Acá es local; en un equipo real sería S3/HCP con *locking*. | Discutido en `docs/decisiones.md` D-19. |
| **Workspace** | Un estado separado dentro del mismo directorio. Lo usamos para `dev` y `prod`. | `terraform workspace select prod`. |
| **Plan / Apply / Destroy** | Calcular el diff / ejecutarlo / borrar todo lo administrado. | `make plan ENV=prod`, `make app ENV=prod`, `make destroy-app ENV=prod`. |
| **`count` / `for_each`** | Crear 0, 1 o N copias de un recurso o módulo a partir de un número o de un mapa. | `count = var.persistence ? 1 : 0` en `3-app/datastores.tf`; `for_each = toset(local.workloads)` en `network_policies.tf`. |
| **`dynamic` block** | Generar bloques repetidos (por ejemplo varias reglas `ingress`) a partir de una lista. | `dynamic "ingress"` en `network_policies.tf`. |
| **`depends_on`** | Forzar un orden cuando Terraform no lo deduce solo. | `depends_on = [kind_cluster.this]` en `1-platform/addons.tf`. |
| **`lifecycle`** / precondition | Reglas sobre cómo tratar un recurso; validaciones que abortan el plan. | La precondición "workspace == environment" en `3-app/namespace.tf`. |
| **Lockfile** (`.terraform.lock.hcl`) | Fija las versiones exactas de los providers. Sí se versiona. | Uno por capa. |

## 3. Cómo se lee HCL (el lenguaje de Terraform)

```hcl
# Un bloque: tipo, etiquetas y un cuerpo con atributos.
resource "docker_network" "kind" {          # tipo = docker_network, nombre lógico = kind
  name   = var.docker_network_name          # referencia a una variable
  driver = "bridge"

  ipam_config {                             # bloque anidado (sub-estructura del recurso)
    subnet  = var.docker_network_subnet     # "172.30.0.0/24" viene de variables.tf
    gateway = var.docker_network_gateway
  }
}

# Referenciar un recurso desde otro crea una dependencia automática:
resource "docker_container" "registry" {
  networks_advanced {
    name = docker_network.kind.name         # tipo.nombre.atributo -> Terraform crea la red antes
  }
}
```

Reglas prácticas:
- `var.x` es una variable, `local.x` un local, `module.x.y` el output `y` del módulo `x`,
  `tipo.nombre.attr` un atributo de un recurso, `data.tipo.nombre.attr` uno de un data source.
- `"texto ${expresión}"` interpola; `[a, b]` es una lista; `{ k = v }` es un mapa;
  `cond ? a : b` es un condicional; `[for x in lista : f(x) if cond]` es una comprensión.
- `merge(m1, m2)` une mapas (el segundo pisa al primero); `concat`, `join`, `split`, `sha1`,
  `yamlencode`, `pathexpand` son funciones incorporadas (no hay funciones definidas por el usuario).
- El orden de los archivos y de los bloques **no importa**: Terraform lee todos los `.tf` del
  directorio y arma el grafo. Por convención los separamos por tema (`variables.tf`,
  `outputs.tf`, `providers.tf`, `main.tf` o nombres descriptivos).
- Los comentarios son `#` o `//`. Los bloques `variable` con `description` y `validation` son
  la documentación viva del módulo: empezá por ahí.

## 4. El ciclo de trabajo

```bash
cd terraform/1-platform
terraform init        # descarga providers a .terraform/ y respeta .terraform.lock.hcl
terraform validate    # chequea sintaxis y tipos
terraform plan        # muestra qué crearía/cambiaría/borraría (no toca nada)
terraform apply       # ejecuta el plan (pide confirmación; -auto-approve la omite)
terraform output      # muestra los outputs
terraform state list  # lista lo que está en el estado
terraform destroy     # borra todo lo del estado (en orden inverso)
```

En la capa 3 se agrega el workspace y el archivo de variables:

```bash
cd terraform/3-app
terraform workspace select prod
terraform plan  -var-file=../environments/prod.tfvars
terraform apply -var-file=../environments/prod.tfvars
```

El `Makefile` de la raíz envuelve todo esto (`make plan ENV=prod` hace exactamente eso).
Leelo: es la lista de "verbos" del proyecto.

Cómo leer un plan: `+` crea, `~` modifica en el lugar, `-` destruye, `-/+` destruye y recrea;
`(known after apply)` es un valor que recién se conoce al crear el recurso. La última línea
`Plan: X to add, Y to change, Z to destroy` es lo primero a mirar.

## 5. Mapa del repo y orden de lectura recomendado

Leé en este orden; en cada archivo, lo que hay que entender está marcado.

1. **`README.md`** y **`docs/how-to.md` §2 y §3**: qué hay y cómo se levanta (10 min).
2. **`docs/img/arquitectura.png`**: tené el diagrama abierto mientras leés código; cada caja del
   diagrama es un recurso Terraform.
3. **`terraform/1-platform/variables.tf`**: los "perillas" de la plataforma: bloques CIDR,
   cantidad de workers, puertos, versiones. Cada variable tiene descripción.
4. **`terraform/1-platform/network.tf`** (30 líneas): la red Docker. Es el ejemplo más chico
   de un recurso completo.
5. **`terraform/1-platform/registry.tf`** y **`cluster.tf`** (el archivo más importante de la
   capa 1): el clúster kind con su topología (bloque `node` por nodo), los CIDR de pods y
   services (`networking`), los puertos publicados (`extra_port_mappings`) y el mount del
   `hosts.toml` del registry. Fijate cómo `dynamic "node"` genera N workers desde
   `var.worker_count`.
6. **`terraform/1-platform/addons.tf`**: cómo se instala un chart de Helm desde Terraform y
   por qué ingress-nginx va en el nodo edge (`nodeSelector`, `hostPort`).
7. **`terraform/1-platform/providers.tf`**: cómo los providers de Kubernetes y Helm reciben las
   credenciales del clúster recién creado.
8. **`terraform/2-images/main.tf`**: cómo se calcula el tag (hash del código) y cómo se
   construye y publica una imagen. Es un buen ejemplo de `for_each` sobre un mapa y de
   `terraform_remote_state`.
9. **`terraform/modules/microservice/main.tf`** (el archivo más importante de la capa 3): el
   patrón que repiten los 5 servicios. Compará con el YAML original
   `the-store/dist/kubernetes.yaml`: es lo mismo, pero parametrizado y con hardening.
   Después `variables.tf` del módulo (qué se puede configurar) y `outputs.tf`.
10. **`terraform/3-app/services.tf`**: las 5 instancias del módulo. Leé `ui` y `orders`: se ve
    cómo cambian las variables de entorno según `var.persistence` (`merge` + condicional).
11. **`terraform/3-app/datastores.tf`** y **`modules/datastore/main.tf`**: bases de datos como
    StatefulSets, contraseñas con `random_password` que terminan en Secrets.
12. **`terraform/3-app/network_policies.tf`**: la tabla `flows` y cómo se convierte en objetos
    NetworkPolicy con `for_each` + `dynamic`. Es la parte más "de redes" del código.
13. **`terraform/3-app/ingress.tf`** y **`namespace.tf`**: exposición HTTP/HTTPS y la
    precondición del workspace.
14. **`terraform/environments/dev.tfvars` y `prod.tfvars`**: ahora que entendés las variables,
    fijate que la única diferencia entre entornos es este archivo.
15. **`scripts/*.sh`**: qué prueba cada demo. Son bash cortos y comentados.
16. **`docs/decisiones.md`**: el porqué de cada cosa. Para el oral es el documento central.

Archivos que podés ignorar: todo lo que hay dentro de `the-store/` (es el código de la
aplicación, ver §7), `.terraform/` (providers descargados), `*.tfstate` (estado).

## 6. Ejercicios para aprender tocando (con el clúster levantado)

Todos son reversibles; el patrón es siempre **cambiar → `plan` → mirar el diff → `apply` →
verificar → volver atrás**.

1. **Ver el estado**: `cd terraform/3-app && terraform workspace select dev && terraform state list`.
   Después `terraform state show module.ui.kubernetes_deployment_v1.this` para ver cómo
   Terraform "recuerda" un recurso.
2. **Cambiar una réplica**: en `environments/dev.tfvars` poné `catalog = 2`; `make plan ENV=dev`
   muestra `~ replicas "1" -> "2"`; `make app ENV=dev`; `kubectl -n the-store-dev get pods`.
   Volvé a 1.
3. **Cambiar el tema de la UI**: `make app ENV=dev` con `ui_theme = "green"` en el tfvars;
   abrí `http://dev.the-store.localhost`. Fijate en el plan que cambian *dos* recursos (el
   ConfigMap y el Deployment, por la anotación `config-hash`). ¿Por qué hace falta la anotación?
   (respuesta: `docs/decisiones.md` D-15 y el comentario en `modules/microservice/main.tf`).
4. **Provocar drift**: `make drift-demo ENV=dev` y leé el plan que imprime.
5. **Agregar un flujo de red**: en `prod`, agregá `{ from = "catalog", to = "orders", port = 8080 }`
   a `app_flows` en `network_policies.tf`, mirá el plan (dos políticas cambian: `allow-catalog`
   gana un `egress`, `allow-orders` un `ingress`), aplicá, y corré `make netpol-test ENV=prod`:
   ahora la prueba "catalog -> orders (no declarado)" falla porque *sí* está declarado. Revertí.
6. **Romper algo a propósito**: cambiá `pod_subnet` en `1-platform/variables.tf` a un bloque
   que se solape con `172.30.0.0/24` y mirá qué pasa en `terraform plan` (pista: kind obliga a
   recrear el clúster: `-/+`). No apliques.
7. **Leer un plan grande**: `make destroy-app ENV=dev` muestra 22 recursos a borrar; `make app
   ENV=dev` los vuelve a crear en un minuto.

## 7. Qué es The Store y qué nos importa de ella

**The Store es una página web**: una tienda online de demostración (vende "gadgets de espía"
ficticios). Es un fork del *retail-store-sample-app* de AWS, una aplicación que AWS publica
justamente para que la gente practique cómo desplegar microservicios. Podés verla ahora mismo
en `http://dev.the-store.localhost` y `https://the-store.localhost` (ya está corriendo en la
notebook; si la reiniciaste, `make up` la vuelve a levantar en 5 minutos).

Está compuesta por **cinco programas independientes** (microservicios), cada uno en su propio
contenedor y escrito en un lenguaje distinto, que se hablan entre sí por HTTP:

| Servicio | Lenguaje | Qué hace | De qué depende (en `prod`) |
|---|---|---|---|
| `ui` | Java / Spring Boot | La página web que ve el usuario. Llama a los otros cuatro. | catalog, carts, orders, checkout |
| `catalog` | Go | Lista de productos (6 productos) | MariaDB (MySQL) |
| `carts` | Java / Spring Boot | Carrito por sesión | DynamoDB Local |
| `orders` | Java / Spring Boot | Crea y guarda órdenes; publica un evento por cada orden | PostgreSQL + RabbitMQ |
| `checkout` | Node / NestJS | Orquesta la compra (dirección, envío, pago) y llama a `orders` | Redis |

Flujo de una compra: navegador → `ui` → `catalog` (mostrar productos) → `carts` (agregar) →
`checkout` (tres pasos) → `orders` (crear la orden en PostgreSQL y avisar por RabbitMQ) → `ui`
muestra la confirmación. El *smoke test* (`scripts/smoke-test.sh`) recorre exactamente ese
camino con `curl`.

**Qué NO nos importa**: el código Java/Go/Node de la app. No lo tocamos ni lo explicamos; es
la "carga" que corre sobre nuestra infraestructura. Otros grupos hacen CI/CD, monitoreo, etc.
sobre la misma app.

**Qué SÍ nos importa** (y es lo que preguntan):
- Cómo se **empaqueta** (imágenes de contenedor, `Dockerfile` de cada servicio, el registry).
- Cómo se **configura**: cada servicio se configura por **variables de entorno**
  (`RETAIL_*`). Por ejemplo `RETAIL_CATALOG_PERSISTENCE_PROVIDER=mysql` o `in-memory`. Eso es lo
  que distingue `dev` de `prod` y está en `services.tf`. Los `README.md` de cada servicio en
  `the-store/src/<servicio>/` documentan sus variables.
- Cómo se **despliega** en Kubernetes: cuántas réplicas, qué puertos, qué chequeos de salud
  (`/health`, `/actuator/health/readiness`), qué recursos de CPU/memoria.
- Cómo se **conectan**: `ui` encuentra a `catalog` por el nombre DNS `catalog` (un Service de
  Kubernetes) en el puerto 80; el Service reenvía al pod en el 8080. Esa red interna (IPs,
  DNS, NAT, políticas) es el corazón del TP para una materia de redes.
- Cómo **entra el usuario**: navegador → puerto 80/443 del host → ingress → `ui`.

Comandos para "tocarla" desde adentro (con `export KUBECONFIG=~/.kube/the-store.kubeconfig`):

```bash
kubectl -n the-store-prod get pods -o wide                 # dónde corre cada pieza y con qué IP
kubectl -n the-store-prod exec deploy/ui -- curl -s http://catalog/catalogue | head -c 300   # la API del catálogo, vista desde ui
kubectl -n the-store-prod exec deploy/ui -- curl -s http://orders/orders | head -c 300       # órdenes guardadas
kubectl -n the-store-prod exec orders-mq-0 -- rabbitmqctl list_queues                        # eventos publicados
kubectl -n the-store-prod logs deploy/checkout --tail=20                                     # logs de un servicio
kubectl -n the-store-prod get configmap ui -o yaml                                           # cómo está configurada la ui
```

## 8. Kubernetes mínimo para leer los módulos

| Objeto | Para qué sirve | Dónde aparece |
|---|---|---|
| **Pod** | La unidad mínima: uno o más contenedores con una IP propia. No se crean a mano. | Los crea el Deployment/StatefulSet. |
| **Deployment** | Mantiene N réplicas de un pod (sin estado) y hace *rolling updates*. | `modules/microservice`. |
| **StatefulSet** | Como Deployment pero con identidad estable y volumen propio (bases de datos). | `modules/datastore`. |
| **Service (ClusterIP)** | Nombre DNS + IP virtual estable delante de los pods; balancea a nivel TCP. | Uno por servicio y por datastore. |
| **Ingress** | Regla HTTP: "el host X va al Service Y". Lo ejecuta ingress-nginx. | `3-app/ingress.tf`. |
| **Namespace** | Carpeta lógica (nombres, permisos). No aísla red por sí solo. | `the-store-dev`, `the-store-prod`. |
| **ConfigMap / Secret** | Configuración / credenciales que se inyectan como variables de entorno. | Módulos. |
| **PVC** | Pedido de disco persistente para un pod. | Datastores. |
| **HPA** | Autoscaler: agrega réplicas cuando la CPU supera un umbral. | `ui` en prod. |
| **NetworkPolicy** | Regla de firewall entre pods (quién puede hablar con quién y por qué puerto). | `network_policies.tf`. |
| **kubectl** | La CLI de Kubernetes. `get`, `describe`, `logs`, `exec` es el 90 % del uso. | Scripts y demos. |

## 9. IDE y herramientas

- **JetBrains** (lo que ya usás): abrí la carpeta `the-store-iac` con IntelliJ IDEA (Community
  alcanza) o cualquier IDE de la familia. Instalá el plugin **"Terraform and HCL"** (oficial de
  JetBrains, gratuito): resaltado, autocompletado de atributos de cada provider, "ir a la
  definición" de variables y módulos, y errores en vivo. Útiles también: **Kubernetes** (para
  los YAML y para ver el clúster desde el IDE, cargando `~/.kube/the-store.kubeconfig`) y
  **Makefile Language**. Si el IDE ofrece importar los proyectos Maven de `the-store/src`,
  decile que no (o marcá `the-store` como *Excluded* en Project Structure): no hace falta y
  ralentiza la indexación.
- **VS Code** es la alternativa: extensión "HashiCorp Terraform" + "Kubernetes".
- **Terminal**: `terraform`, `kubectl`, `docker`, `make`. Ya están instalados en la notebook
  (`~/.local/bin`). Para otra máquina, ver `docs/how-to.md` §1.
- Formateo automático: `make fmt` (`terraform fmt`), que todos deberían correr antes de commitear.
- Para ver el clúster gráficamente: `k9s` (terminal) o el plugin de Kubernetes del IDE. No es
  necesario, pero ayuda a "ver" pods, logs y eventos.

## 10. Referencias

- Terraform, tutorial oficial de conceptos (30 min): https://developer.hashicorp.com/terraform/intro
- Lenguaje HCL (referencia): https://developer.hashicorp.com/terraform/language
- Providers usados: `kreuzwerker/docker`, `tehcyx/kind`, `hashicorp/kubernetes`,
  `hashicorp/helm` en https://registry.terraform.io (cada recurso tiene su página con todos los
  atributos; es lo que hay que abrir cuando no se entiende un bloque).
- kind (Kubernetes in Docker): https://kind.sigs.k8s.io/docs/user/quick-start/
- Kubernetes, conceptos: https://kubernetes.io/docs/concepts/
- The Store original (AWS retail-store-sample-app): https://github.com/aws-containers/retail-store-sample-app
- Este repo: `docs/decisiones.md` (el porqué), `docs/how-to.md` (el cómo),
  `docs/presentacion.md` (qué se muestra), `docs/resumen-clases.md` (el puente con la materia).
