# Decisiones de diseño y alternativas descartadas

Registro de todas las decisiones tomadas en el TP, con las alternativas que se
evaluaron y por qué se descartaron. Es el documento interno del grupo: sirve
para responder preguntas en la presentación y para no volver a discutir lo
mismo. La pre-entrega (`preentrega.pdf`) resume las más importantes.

## 1. Herramienta: Terraform

**Alternativas:** Pulumi, OpenTofu, AWS CloudFormation, AWS CDK, Ansible, Helm.

- **Pulumi** declara infraestructura con lenguajes de propósito general
  (TypeScript, Python, Go). Es potente, pero el código mezcla lógica de
  programación con declaración de recursos y el plan de cambios es menos
  directo de leer. HCL es un lenguaje declarativo diseñado para esto y el tema
  asignado nombra a Terraform.
- **OpenTofu** es la bifurcación de código abierto de Terraform (licencia MPL)
  y es compatible con nuestro código; se mantuvo Terraform por ser la
  herramienta del tema. Si el día de mañana la licencia BSL fuera un problema,
  cambiar es reemplazar el binario.
- **CloudFormation / CDK** sólo funcionan en AWS y no manejan los objetos de
  Kubernetes ni las imágenes: habría que combinarlos con otra herramienta.
  Terraform cubre todo (AWS, Kubernetes, Helm, Docker) con un solo estado.
- **Ansible** está orientado a configurar servidores que ya existen y no
  mantiene un estado contra el cual comparar la realidad (no detecta drift).
- **Helm / Kustomize** alcanzan sólo a los objetos de Kubernetes; no crean la
  VPC, el clúster ni las bases. Helm se usa igual, invocado desde Terraform,
  para instalar el Ingress Controller.

## 2. Plataforma: AWS con EKS (antes: kind)

**Historia.** El primer prototipo corrió sobre kind (Kubernetes en Docker), la
misma herramienta que usa el script `local.sh` de la cátedra. Fue gratuito y
sirvió para validar el módulo de aplicación (Deployments, Services, Ingress y
NetworkPolicies) con pruebas de punta a punta. Esa versión quedó en la rama
`version-kind` (y una anterior, más elaborada, en `version-completa`).

**Por qué se cambió a AWS/EKS:**

- El TP se va a desplegar en AWS; con kind no se puede mostrar nada de red
  real (subredes, ruteo, NAT, security groups), que es el foco de la materia.
- kind no permite agregar nodos a un clúster existente (hay que recrearlo),
  así que el caso de uso de escalamiento sólo podía tocar réplicas.
- kind no tiene balanceadores ni bases de datos administradas: había que
  correr MySQL, PostgreSQL, Redis, RabbitMQ y DynamoDB-local como pods, algo
  que nadie haría en producción.
- Con EKS todo lo anterior existe de verdad, y Terraform lo crea y lo destruye
  completo, que es justamente el punto del trabajo.

**Costo de la decisión:** ~USD 0,30 por hora de entorno encendido, ~25 minutos
de `apply` y ~15 de `destroy`. Se mitiga creando el entorno por sesión y
destruyéndolo al terminar; el estado remoto y el código lo recrean idéntico.

**Alternativas en AWS descartadas:** ECS/Fargate (más simple, pero la
aplicación viene preparada para Kubernetes y el enunciado habla de clúster);
instancias EC2 con Kubernetes instalado a mano (kubeadm): mucho trabajo sin
valor para el tema; Minikube/k3s en una EC2: mismas limitaciones que kind.

## 3. Estructura del código: una raíz y cinco módulos

**Alternativas:** un único archivo plano; varias "capas" con estados separados
(red / clúster / aplicación), como en la rama `version-completa`.

Se eligió **una configuración raíz con cinco módulos** (`red`, `cluster`,
`imagenes`, `datos`, `aplicacion`), un solo estado y un solo
`terraform.tfvars`:

- Un archivo plano con ~90 recursos es ilegible; los módulos agrupan por
  responsabilidad y se explican de a uno en la presentación.
- Varias capas con estados separados es lo que se hace en empresas grandes
  (para que equipos distintos apliquen por separado), pero para un POC agrega
  tres `init/plan/apply` encadenados y pasar outputs entre estados. La
  revisión de la pre-entrega del otro grupo mostró que un solo estado es el
  nivel de complejidad esperado.

La disposición de archivos (`main.tf`, `variables.tf`, `outputs.tf`, módulos
bajo `modules/`) es la estructura estándar que documenta HashiCorp; los módulos
llevan nombres en castellano, como los comentarios y la documentación.

Cada módulo expone sólo lo que el siguiente necesita (`vpc_id`, subredes,
security group de los nodos, endpoints de las bases, imágenes). Los valores
concretos del entorno están **sólo** en `terraform.tfvars`; las variables
tienen descripción y valor por defecto en `variables.tf`.

## 4. Red: VPC escrita a mano

**Alternativa:** el módulo comunitario `terraform-aws-modules/vpc/aws`.

El módulo resuelve todo en diez líneas, pero esconde exactamente lo que la
materia estudia: subredes, tablas de ruteo, Internet Gateway, NAT. Escribirlo a
mano son unas quince declaraciones (`modules/red/main.tf`) que se
pueden leer y explicar en cinco minutos. Para el clúster se tomó la decisión
inversa (ver 6).

### Diseño de direccionamiento

| Bloque | Uso | Por qué |
|---|---|---|
| `10.0.0.0/16` | VPC | Privado (RFC 1918), 65.534 direcciones, el clásico de AWS. |
| `10.0.0.0/24`, `10.0.1.0/24` | Subredes públicas (una por AZ) | Sólo alojan el ALB y el NAT Gateway: unas pocas IPs. |
| `10.0.16.0/20`, `10.0.32.0/20` | Subredes privadas (una por AZ) | Nodos y **pods**. 4.091 IPs cada una. |
| `10.0.48.0/24`, `10.0.49.0/24` | Subredes de datos (una por AZ) | RDS y ElastiCache. Sin ninguna ruta a Internet. |
| `172.20.0.0/16` | Services de Kubernetes (ClusterIP) | Virtual, sólo existe en reglas DNAT de kube-proxy. Disjunto de la VPC. |

- Las privadas son grandes porque en EKS el plugin **VPC CNI** le da a cada
  pod una IP de la subred del nodo (no un bloque aparte como en kind). Un
  `t3.medium` puede tener hasta 17 pods; con /24 alcanzaría hoy, pero /20
  deja crecer sin renumerar. Es VLSM aplicado: subredes de distinto tamaño
  según lo que alojan.
- Las subredes de datos son una capa aparte (diseño clásico de tres capas:
  DMZ, aplicación, datos) con su propia tabla de ruteo sin ruta por defecto:
  aunque un security group fallara, una base no tendría por dónde salir a
  Internet. Alcanza con /24: una IP por base.
- Quedan libres `10.0.2.0/24`-`10.0.15.0/24` y a partir de `10.0.50.0` para
  agregar zonas o subredes sin cambiar nada de lo existente.
- `172.20.0.0/16` es el valor por defecto de EKS para el bloque de servicios;
  se declara explícitamente (`service_ipv4_cidr`) para que aparezca en el
  código y en el diagrama. CoreDNS queda en `172.20.0.10`.

### VPC Endpoints de tipo Gateway para S3 y DynamoDB

Se agregan a la tabla de ruteo privada rutas hacia S3 y DynamoDB que quedan
dentro de la red de AWS: no cuestan nada, el tráfico no pasa por el NAT (las
capas de las imágenes de ECR vienen de S3, así que ahorra tráfico de NAT) y es
lo que hace un diseño AWS serio. **Se descartó ir más lejos y sacar el NAT
Gateway** (operar la VPC sin salida a Internet, sólo con endpoints): haría
falta un endpoint de tipo *Interface* por cada servicio que usan los nodos
(ECR API, ECR registro, EC2 para el plugin de red, SQS, STS para IRSA y ELB
para el controlador del balanceador), que a ~0,01 USD/h por zona cuestan más
que el NAT, y además replicar en ECR la imagen del AWS Load Balancer
Controller, que se publica en el ECR público. Mucho más que puede fallar, sin
nada nuevo que demostrar.

### Dos zonas de disponibilidad, un solo NAT Gateway

EKS exige subredes en al menos dos zonas. Se usan `us-east-1a` y `us-east-1b`
(en `us-east-1e` EKS no está disponible). El NAT Gateway se pone **uno solo**,
en la subred pública de la primera zona (~USD 33/mes cada uno): en producción
iría uno por zona para que la caída de una zona no deje sin salida a la otra;
en el POC no se justifica y está documentado como mejora.

**Alternativa descartada:** poner los nodos en subredes públicas con IP pública
y sin NAT (más barato). Se descartó porque contradice el diseño DMZ / red
interna que se quiere mostrar: los nodos y las bases no tienen que ser
alcanzables desde Internet.

## 5. Punto de entrada: Application Load Balancer con el AWS Load Balancer Controller

**Alternativas:** Ingress Controller nginx publicado por un Network Load
Balancer (fue la primera versión del código); un Classic Load Balancer;
exponer la UI con un Service de tipo LoadBalancer sin Ingress.

Se eligió el **ALB** (decisión del grupo del 22/09/2026: es el balanceador que
los integrantes conocen de la materia de AWS y el camino recomendado por AWS
para EKS):

- El **AWS Load Balancer Controller** corre en el clúster, observa los objetos
  Ingress y crea por cada uno un ALB en las subredes públicas (las etiquetadas
  con `kubernetes.io/role/elb`), con sus target groups, listeners y security
  groups. Con `target-type: ip` registra directamente las IPs de los pods de
  la UI: el pedido HTTP va del ALB al pod sin pasar por NodePort ni por un
  proxy intermedio.
- Cuesta algo de infraestructura extra, toda en `modules/cluster`: un rol IAM
  que el controlador asume a través de su service account (IRSA, con el
  proveedor OIDC que el módulo de EKS ya crea) y la política oficial del
  controlador (la trae el módulo comunitario de IAM,
  `attach_load_balancer_controller_policy`), más el chart del controlador.
- **nginx + NLB** era más liviano (un chart, sin IAM) y muestra bien la
  diferencia entre capa 4 y capa 7, pero agrega un salto (NLB → NodePort →
  nginx → pod) y pods de nginx que operar. Queda descartado; el código de esa
  versión está en el historial de git.
- Un Classic Load Balancer está en vías de retiro. Sin Ingress no habría un
  único punto de entrada declarado en Kubernetes.

Consecuencias en el resto del código: la NetworkPolicy de la UI ya no permite
"desde el namespace del ingress" sino desde los bloques de las subredes
públicas, que es donde viven las interfaces del ALB; el nombre DNS de la
tienda sale del `status` del Ingress (`wait_for_load_balancer = true`); y en
el `destroy` el Ingress se borra antes que el controlador (Terraform lo
garantiza por las dependencias), para que el controlador alcance a eliminar el
ALB y no quede huérfano.

Sin dominio propio, el Ingress no fija `host` y la tienda se accede por el
nombre DNS del ALB (`terraform output url`). TLS queda fuera de alcance.

## 6. Clúster: módulo comunitario `terraform-aws-modules/eks`

**Alternativa:** escribir `aws_eks_cluster`, `aws_eks_node_group`, los roles y
políticas de IAM, los security groups del plano de control y de los nodos, los
add-ons y las entradas de acceso a mano.

Son ~300 líneas de IAM y security groups que no aportan al análisis de red y en
las que es fácil equivocarse (un puerto que falta y los nodos no se unen al
clúster). El módulo es el estándar de facto, está mantenido y documenta cada
regla. Lo que sí se declara explícitamente en `modules/cluster/main.tf`:
versión de Kubernetes, subredes privadas, bloque de servicios, endpoint
público del API server, tipo y cantidad de nodos, y los add-ons.

Decisiones dentro del clúster:

- **Kubernetes 1.34** (variable): la última versión estándar de EKS al momento
  de escribir; si AWS la retira, `aws eks describe-cluster-versions` lista las
  vigentes.
- **Nodos `t3.medium` con Amazon Linux 2023** (2 vCPU, 4 GB): cinco
  microservicios Java/Go/Node con 256-512 MB cada uno más el Ingress Controller
  y CoreDNS necesitan ~3 GB en total; `t3.small` (2 GB) no alcanza para que
  todo quede en un nodo si el otro cae. AL2023 es la imagen por defecto de
  EKS; AL2 está en fin de vida.
- **Metadatos de instancia con `http_put_response_hop_limit = 2`**: los pods
  de carts y orders usan las credenciales del rol del nodo, que se obtienen
  del servicio de metadatos (IMDS). El módulo de EKS deja el límite en un
  salto (buena práctica: los pods no ven el IMDS), con lo cual los pods no
  tendrían credenciales; con dos saltos lo alcanzan. Es el precio de no usar
  IRSA por microservicio (ver 8).
- **Grupo de nodos con `min = max = desired = node_count`**: el módulo ignora
  cambios de `desired_size` después de crear el grupo (para no pelearse con un
  autoescalador). Fijando los tres al mismo valor, cambiar `node_count` en el
  tfvars escala el grupo hacia arriba y hacia abajo, que es lo que el caso de
  uso 2 necesita. Autoescalado automático queda fuera de alcance.
- **API server con endpoint público**: hace falta para operar el clúster desde
  nuestras máquinas y para que Terraform cree los objetos de Kubernetes. Sigue
  autenticado con IAM (`aws eks get-token`). La alternativa (endpoint privado +
  bastión o VPN) es lo correcto en producción pero agrega una EC2 y un túnel al
  POC.
- **Add-on VPC CNI con `enableNetworkPolicy = true`**: es lo que hace que las
  NetworkPolicies se apliquen (por defecto EKS las acepta pero no las hace
  cumplir). La alternativa era instalar Calico; el agente de AWS viene en el
  add-on y no requiere nada más.

## 7. Imágenes: construidas por Terraform y publicadas en ECR

**Alternativas:** usar las imágenes públicas de AWS
(`public.ecr.aws/aws-containers/retail-store-sample-*`); construirlas con un
pipeline de CI; construirlas a mano con `docker build` y `docker push`.

- Las imágenes públicas funcionarían, pero no se podría demostrar el caso de
  uso 3 (cambiar `app_version` y ver el rolling update de **nuestra** build).
- Un pipeline de CI es el tema de otro grupo y está fuera de alcance.
- Construirlas a mano es otro script imperativo, lo que se quiere evitar.

El provider `docker` construye las cinco imágenes (`docker_image`, plataforma
`linux/amd64` porque los nodos son x86) y las publica (`docker_registry_image`)
en un repositorio ECR por servicio, autenticado con un token de ECR que
Terraform pide en cada corrida (`aws_ecr_authorization_token`, dura 12 horas).
Los nodos las descargan con el permiso de lectura de ECR que el módulo de EKS
les da. `force_delete = true` en los repositorios permite que el `destroy` los
borre con imágenes adentro.

## 8. Capa de datos: servicios administrados

En kind las bases corrían como pods. En AWS se usa el servicio administrado
que la aplicación ya soporta para cada persistencia:

| Servicio | En kind | En AWS | Motivo |
|---|---|---|---|
| catalog | MySQL en un pod | **RDS MySQL 8.0** | Mismo motor, administrado. |
| orders | PostgreSQL en un pod | **RDS PostgreSQL 17** | Ídem. |
| orders (mensajería) | RabbitMQ en un pod | **SQS** | La app tiene proveedor `sqs`; evita operar un broker. |
| carts | DynamoDB-local en un pod | **DynamoDB** (PAY_PER_REQUEST) | Es el servicio real; la app ya lo usa. |
| checkout | Redis en un pod | **ElastiCache Redis 7.1** | Mismo motor, administrado. |

- **RDS y ElastiCache** viven en las subredes de datos, sin IP pública ni
  ruta a Internet, dentro de un security group (`the-store-data`) que sólo
  acepta 3306, 5432 y 6379 **desde el security group de los nodos**. Es el equivalente de la regla
  de firewall "sólo la red interna llega a las bases"; las NetworkPolicies no
  pueden cubrirlo porque las bases están fuera del clúster.
- **DynamoDB y SQS** no tienen red propia (son endpoints HTTPS regionales): a
  DynamoDB se llega por el VPC Endpoint de tipo Gateway y a SQS por el NAT
  Gateway, y el acceso se controla con **IAM**: una política con las acciones
  mínimas sobre la tabla y la cola, adjunta al rol de los nodos, que los pods
  heredan.
- **Alternativa descartada: IAM Roles for Service Accounts / Pod Identity**
  (un rol por microservicio, de modo que sólo carts pueda leer la tabla y sólo
  orders escribir en la cola). Es la práctica recomendada y queda documentada
  como mejora; para el POC agrega un proveedor OIDC, cinco roles y cinco
  service accounts sin cambiar nada de lo que se demuestra.
- **Contraseñas** generadas con el provider `random` y pasadas como variables
  de entorno a los pods marcadas `sensitive` (no se imprimen en el plan). La
  alternativa (AWS Secrets Manager + un operador que las inyecte) es mejor en
  producción pero agrega un componente más. Las contraseñas quedan en el
  estado, por eso el estado está en un bucket privado con versionado.
- **Ajustes de POC** que en producción serían distintos: `db.t3.micro` y
  `cache.t3.micro` (los más chicos), sin Multi-AZ, sin backups automáticos
  (`backup_retention_period = 0`), sin snapshot final y sin protección contra
  borrado, para que el `destroy` sea rápido y no deje nada.

## 9. Segmentación dentro del clúster: NetworkPolicies

Se aplican cuatro reglas (`modules/aplicacion/network_policies.tf`), basadas
en las etiquetas `app` y `tier` de los pods:

1. `default-deny`: ningún pod del namespace acepta conexiones entrantes.
2. `allow-ui-from-alb`: la UI acepta 8080/TCP sólo desde los bloques de las
   subredes públicas, donde viven las interfaces del ALB (y desde donde llegan
   sus health checks).
3. `allow-backends-from-app`: los backends aceptan 8080/TCP desde pods con
   `tier` frontend o backend (la UI y, entre ellos, checkout → orders).
4. `cuarentena`: un pod con `tier = cuarentena` no puede recibir ni iniciar
   conexiones (Ingress y Egress vacíos).

**Cuarentena por etiqueta.** La variable `quarantine` (lista de servicios)
cambia la etiqueta `tier` del pod a `cuarentena`. Con eso el pod deja de
coincidir con las reglas de permiso y pasa a coincidir con la de bloqueo
total. Se eligió así porque el `plan` muestra un único cambio pequeño y
comprensible (una etiqueta), en vez de crear y borrar objetos. La alternativa
era escalar el servicio a cero réplicas: también lo "apaga", pero destruye la
evidencia del incidente y no es una medida de red.

**Egreso.** Sólo se restringe el egreso del pod en cuarentena. Restringir el
egreso de todos los pods (sólo DNS + destinos permitidos) es más seguro pero
complica las reglas hacia RDS/DynamoDB/SQS (IPs que cambian) y no agrega nada
a los casos de uso.

## 10. Estado remoto en S3 con bloqueo nativo

**Alternativas:** estado local (archivo en la máquina); S3 + tabla DynamoDB
para el bloqueo (el esquema clásico); Terraform Cloud.

- El estado local no sirve con tres personas: cada una tendría su propia
  "verdad" y pisaría a las demás.
- Desde Terraform 1.10 el backend S3 bloquea con un archivo `.tflock` en el
  mismo bucket (`use_lockfile = true`); la tabla DynamoDB ya no hace falta.
- Terraform Cloud funciona, pero agrega una cuenta más y no es AWS.

El bucket se crea con una configuración aparte (`terraform/bootstrap/`) porque
el estado no puede guardarse en un bucket que la misma configuración crea. Ese
bootstrap usa estado local y no se versiona: el bucket se identifica por su
nombre. El bucket tiene versionado (historial de cada `apply`, y se puede
recuperar un estado anterior) y acceso público bloqueado, porque el estado
contiene las contraseñas de las bases.

## 11. Etiquetas y control de costos

Todos los recursos reciben `Project = the-store` y `ManagedBy = terraform`
mediante `default_tags` del provider. Sirve para ver el gasto del TP en la
consola de facturación y para encontrar recursos huérfanos (Tag Editor) si un
`destroy` fallara a la mitad. El costo estimado del entorno es ~USD 0,30/h; la
regla del grupo es **destruir al terminar cada sesión**.

## 12. Fuera de alcance (y por qué)

| Tema | Motivo |
|---|---|
| Dominio propio y TLS | Requiere comprar un dominio; el ALB sin TLS alcanza para demostrar la infraestructura. |
| Integración continua | Tema de otro grupo. |
| Observabilidad, logs centralizados, service mesh | Temas de otros grupos. |
| Autoescalado (HPA / Cluster Autoscaler / Karpenter) | El escalamiento se demuestra por configuración, que es lo que muestra a Terraform. |
| Multi-AZ en RDS, NAT por zona, IRSA | Buenas prácticas de producción documentadas como mejoras; duplican costo o agregan piezas sin cambiar la demo. |

## 13. Estado de las pruebas

- **Validación estática** (`terraform fmt -check`, `terraform validate` en la
  raíz y en `bootstrap/`): pasa.
- **Versión kind** (rama `version-kind`): probada de punta a punta, incluidos
  los cuatro casos de uso y `verificar.sh` (19/19). El módulo de aplicación es
  el mismo, con la capa de datos apuntando ahora a los servicios de AWS.
- **Versión AWS**: pendiente de la primera corrida real. Las credenciales de
  AWS las entrega la cátedra para la entrega final; hasta entonces sólo hay
  validación estática. Cuando se haga: `apply` completo, `verificar.sh`, los
  cuatro casos de uso y `destroy`, y actualizar esta sección y los tiempos del
  README.
- **Riesgo a consultar con la cátedra: qué tipo de cuenta entregan.** Si es
  una cuenta de AWS Academy (Learner Lab), no se pueden crear roles de IAM:
  hay que usar el rol `LabRole` existente. El módulo de EKS lo contempla
  (`create_iam_role = false` + `iam_role_arn` para el clúster y el grupo de
  nodos) y la política de DynamoDB/SQS se reemplaza por los permisos que ese
  rol ya tiene. Es un cambio acotado en `modules/cluster` y `modules/datos`;
  el resto del código no cambia.
