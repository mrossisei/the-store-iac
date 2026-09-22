# Guía de lectura del código (para quien nunca usó Terraform)

Todo el código está en `terraform/`: son unas 1.400 líneas de HCL repartidas
en 20 archivos, casi la mitad comentarios. Se puede leer entero en una tarde.
Esta guía dice en qué orden leerlo y qué mirar en cada archivo.

## 1. Cinco conceptos que alcanzan

| Concepto | Qué es | Dónde se ve |
|---|---|---|
| **Provider** | Plugin con el que Terraform habla con una plataforma (AWS, Kubernetes, Docker). Se descarga en `terraform init`. | `providers.tf` |
| **Resource** | Una cosa que existe: una VPC, una subred, una base, un Deployment. `resource "tipo" "nombre" { atributos }`. Terraform la crea, la modifica o la borra para que coincida con lo declarado. | todos los `main.tf` |
| **Data source** | Algo que Terraform sólo lee (no crea): un token de ECR, el Service del Ingress Controller. `data "tipo" "nombre"`. | `providers.tf`, `modules/cluster` |
| **Variable / Output** | Entradas y salidas. Las variables se declaran en `variables.tf` y toman valor en `terraform.tfvars`; los outputs muestran resultados (`terraform output`). | `variables.tf`, `outputs.tf` |
| **Module** | Una carpeta con recursos, variables y outputs, que se invoca como una función: `module "x" { source = "./modules/x"; var1 = ... }`. | `main.tf` |

Y el ciclo de trabajo, siempre el mismo:

```
terraform init      descarga providers y módulos, conecta con el estado en S3
terraform plan      compara lo declarado con lo que existe y muestra qué haría
terraform apply     hace los cambios (pide confirmación)
terraform destroy   borra todo lo que administra
```

El **estado** (`terraform.tfstate`, guardado en S3) es la memoria de
Terraform: la lista de recursos que creó y sus IDs reales. Con él sabe qué
cambiar y qué borrar, y detecta drift (algo cambió por fuera).

## 2. Orden de lectura

```
 1. terraform.tfvars                 2 min   los valores del entorno
 2. variables.tf                     5 min   qué significa cada valor
 3. main.tf                          5 min   cómo se conectan los módulos
 4. modules/networking/main.tf      15 min   la red (lo más importante para la materia)
 5. modules/cluster/main.tf         10 min   EKS + Ingress Controller
 6. modules/databases/main.tf       10 min   RDS, ElastiCache, DynamoDB, SQS, security group, IAM
 7. modules/registry/main.tf         5 min   ECR + construcción de imágenes
 8. modules/application/main.tf     10 min   los cinco microservicios
 9. modules/application/network_policies.tf   10 min   quién habla con quién
10. providers.tf, backend.tf, outputs.tf, bootstrap/main.tf   10 min
```

### 2.1 `terraform.tfvars`: los valores

Es el único archivo que se edita en el día a día. Cada caso de uso de la
pre-entrega es cambiar un valor acá y correr `plan` + `apply`: `replicas`,
`node_count`, `app_version`, `quarantine`.

### 2.2 `variables.tf`: qué significa cada valor

Cada `variable` tiene `description`, `type` y `default`. Mirar cómo el tipo
restringe lo que se puede poner: `list(string)` para las subredes,
`map(number)` para las réplicas.

### 2.3 `main.tf`: el cableado

Cinco bloques `module`. Lo importante es **cómo la salida de uno es la entrada
del siguiente**; Terraform deduce de ahí el orden de creación (no hay que
decirle "primero la red"):

```
networking ──vpc_id, private_subnet_ids──▶ cluster ──node_security_group_id, node_role_name──▶ databases
                                              │                                                    │
                                              │  endpoint, CA (providers kubernetes/helm)          │ connection (hosts, passwords)
                                              ▼                                                    ▼
registry ──images────────────────────────▶ application ◀───────────────────────────────────────────┘
```

`local.services` es la tabla "nombre del servicio → carpeta del código
fuente" que usa el módulo `registry` para construir cada imagen.

### 2.4 `modules/networking/main.tf`: la red

Es el archivo para leer con más cuidado. Está en el mismo orden en que se
dibuja la red:

1. `aws_vpc`: el bloque `10.0.0.0/16` con DNS habilitado.
2. `aws_internet_gateway`: la puerta a Internet de la VPC.
3. `aws_subnet.public` y `.private`: usan `count = length(var.azs)` para crear
   una de cada tipo por zona; `count.index` elige el bloque y la zona de cada
   una. Las públicas tienen `map_public_ip_on_launch`; las etiquetas
   `kubernetes.io/role/elb` y `internal-elb` le dicen a Kubernetes dónde crear
   balanceadores.
4. `aws_eip` + `aws_nat_gateway`: la IP pública única con la que salen las
   subredes privadas, ubicada en la primera subred pública.
5. Dos `aws_route_table` con su ruta por defecto (`0.0.0.0/0` → IGW en la
   pública, → NAT en la privada) y las asociaciones con cada subred. La ruta
   `local` de la VPC (todo `10.0.0.0/16` entre sí) la agrega AWS sola.

Ejercicio: seguir el camino de un paquete de un pod (10.0.20.5) hacia
`sqs.us-east-1.amazonaws.com`: tabla de ruteo privada → NAT Gateway (SNAT a la
EIP) → tabla pública → IGW.

### 2.5 `modules/cluster/main.tf`: EKS

- `module "eks"`: se usa el módulo de la comunidad. Lo que declaramos:
  versión, VPC y subredes privadas, bloque de servicios, endpoint público,
  add-ons (CoreDNS, kube-proxy y VPC CNI con NetworkPolicies habilitadas) y
  el grupo de nodos (`t3.medium`, `node_count` fijo como mínimo y máximo).
- `helm_release.ingress_nginx`: instala el Ingress Controller con un Service
  de tipo `LoadBalancer` anotado `nlb`: Kubernetes crea el Network Load
  Balancer en las subredes públicas. `wait = true` hace que Terraform espere
  hasta que el balanceador exista.
- `data.kubernetes_service_v1.ingress`: lee el nombre DNS del balanceador que
  AWS asignó; es lo que sale en `terraform output url`.

### 2.6 `modules/databases/main.tf`: la capa de datos

- `random_password`: dos contraseñas que nadie escribe.
- `aws_security_group.data` + `aws_vpc_security_group_ingress_rule.from_nodes`
  (un `for_each` sobre `{ mysql = 3306, postgres = 5432, redis = 6379 }`): el
  firewall de las bases. Sólo acepta desde el security group de los nodos.
- `aws_db_instance` × 2, `aws_elasticache_cluster`, `aws_dynamodb_table`,
  `aws_sqs_queue`: los cinco servicios. Mirar los comentarios "ajustes de POC".
- `aws_iam_policy` + `aws_iam_role_policy_attachment`: permisos mínimos sobre
  la tabla y la cola para el rol de los nodos.
- `outputs.tf`: `connection` (con contraseñas, marcado `sensitive`) para la
  aplicación y `endpoints` (sin contraseñas) para mostrar.

### 2.7 `modules/registry/main.tf`: imágenes

Tres recursos con `for_each = var.services`: el repositorio ECR, la imagen
construida localmente (`docker_image`, con `build { context = ... }`) y su
publicación (`docker_registry_image`). El tag es `var.app_version`; al
cambiarlo, los tres se recalculan y la aplicación recibe una imagen nueva.

### 2.8 `modules/application/main.tf`: los microservicios

- `local.services`: una tabla con la configuración de cada microservicio
  (capa, ruta de salud, memoria, variables de entorno). Las variables de
  entorno son las que la aplicación documenta: endpoint de MySQL, URL de
  Redis, nombre de la tabla DynamoDB, URL de la cola, etc.
- `kubernetes_deployment_v1.service` y `kubernetes_service_v1.service`: un
  `for_each` sobre esa tabla crea los cinco Deployments y los cinco Services
  con el mismo bloque de código. Notar la etiqueta `tier`, que cambia a
  `cuarentena` si el servicio está en `var.quarantine`.
- `kubernetes_ingress_v1.ui`: la regla "todo `/` va a la UI" para el Ingress
  Controller.

### 2.9 `modules/application/network_policies.tf`: quién habla con quién

Cuatro reglas, explicadas en el encabezado del archivo. Leerlas pensando en
un firewall: deny por defecto, y luego permisos por etiqueta. La cuarentena es
la última: selecciona `tier = cuarentena` y no permite nada en ninguna
dirección.

### 2.10 El resto

- `providers.tf`: versiones de los providers; el de AWS con `default_tags`;
  los de Kubernetes y Helm apuntando al endpoint del clúster con un token de
  `aws eks get-token`; el de Docker autenticado contra ECR.
- `backend.tf`: dónde vive el estado (bucket S3, con bloqueo).
- `bootstrap/main.tf`: crea ese bucket. Es una configuración independiente
  con estado local.
- `outputs.tf`: lo que se ve al final del `apply` y con `terraform output`.

## 3. Cómo se propaga un cambio

Ejemplo: `node_count = 3` en `terraform.tfvars`.

```
terraform.tfvars  (node_count = 3)
   └─▶ variables.tf   variable "node_count"
         └─▶ main.tf   module "cluster" { node_count = var.node_count }
               └─▶ modules/cluster/main.tf   eks_managed_node_groups.workers { min = desired = max = var.node_count }
                     └─▶ AWS: el Auto Scaling Group del grupo de nodos pasa de 2 a 3 instancias
```

`terraform plan` muestra exactamente ese recurso con `2 -> 3` y nada más.

## 4. Sintaxis que aparece y conviene reconocer

| Sintaxis | Significado | Ejemplo en el código |
|---|---|---|
| `var.x` | valor de una variable | `var.vpc_cidr` |
| `module.x.y` | output `y` del módulo `x` | `module.networking.vpc_id` |
| `local.x` | valor calculado local al archivo | `local.services` |
| `count` / `count.index` | N copias del recurso, indexadas | subredes |
| `for_each` / `each.key` / `each.value` | una copia por elemento de un mapa | microservicios, reglas del SG |
| `"${...}"` | interpolación en un string | `"${var.name}-public"` |
| `cond ? a : b` | condicional | etiqueta `tier` en cuarentena |
| `lookup(map, key, default)` | leer un mapa con valor por defecto | réplicas |
| `depends_on` | dependencia explícita cuando no hay referencia | aplicación tras bases e imágenes |
| `sensitive = true` | no mostrar el valor en plan/output | contraseñas |
| `try(expr, default)` | valor por defecto si la expresión falla | hostname del balanceador |

## 5. Herramientas

- **Terraform CLI**: `terraform fmt` (formatea), `terraform validate` (chequea
  sintaxis y tipos sin tocar AWS), `terraform console` (probar expresiones),
  `terraform state list` / `state show` (ver lo que existe),
  `terraform graph | dot -Tpng > grafo.png` (dibujar las dependencias).
- **IDE**: en JetBrains (IntelliJ, PyCharm, ...) el plugin *Terraform and HCL*;
  en VS Code la extensión *HashiCorp Terraform*. Dan autocompletado, ir a la
  definición de una variable o un módulo y documentación de cada atributo.
- **Documentación de los providers**: cada recurso tiene su página en
  `registry.terraform.io` (por ejemplo, `aws_subnet`), con todos los atributos.

## 6. Ejercicios para entenderlo de verdad

1. Cambiar `replicas.ui` a 3 y correr `terraform plan` (sin apply). Leer el
   plan: un solo cambio, `replicas: 2 -> 3`.
2. Agregar una tercera zona (`us-east-1c`) con sus dos bloques en
   `terraform.tfvars` y ver en el plan cuántos recursos aparecen (dos
   subredes y dos asociaciones de tabla de ruteo; el NAT sigue siendo uno).
3. Explicar por qué `module.application` tiene `depends_on` explícito en vez
   de una referencia (pista: la imagen se referencia, pero la publicación en
   ECR y las bases no aparecen en ningún atributo de los Deployments).
4. Buscar en `network_policies.tf` qué regla permite que `checkout` hable con
   `orders`, y qué pasaría si `checkout` tuviera `tier = frontend`.
5. Con el entorno creado: `terraform state show
   'module.networking.aws_route_table.private'` y comparar la ruta con la
   consola de AWS.
