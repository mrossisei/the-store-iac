# The Store - Infraestructura como Código con Terraform (AWS)

Trabajo Práctico Especial de Redes de Información (ITBA, 2C 2026).
Integrantes: Matias Rossi, Juan Pablo Birsa y Federico Viera.

Este repositorio crea con Terraform **toda** la infraestructura que necesita la
tienda *The Store* (cinco microservicios) en AWS: la red (VPC, subredes,
Internet Gateway, NAT Gateway, tablas de ruteo), un clúster EKS con sus nodos,
el balanceador de entrada, los repositorios de imágenes (ECR), las bases de
datos administradas (RDS MySQL, RDS PostgreSQL, ElastiCache Redis, DynamoDB y
SQS) y los objetos de Kubernetes de la aplicación (Deployments, Services,
Ingress y NetworkPolicies). Todo se crea con `terraform apply` y se elimina con
`terraform destroy`.

```
the-store-iac/
├── terraform/                 # Toda la infraestructura
│   ├── main.tf                #   Orquestación de los cinco módulos
│   ├── variables.tf           #   Parámetros (con su descripción)
│   ├── terraform.tfvars       #   Valores concretos del entorno  <-- lo que se edita
│   ├── outputs.tf             #   URL de la tienda, endpoints, bloques de red
│   ├── providers.tf           #   aws, kubernetes, helm, docker, random
│   ├── backend.tf             #   Estado remoto en S3
│   ├── bootstrap/             #   Crea el bucket del estado (una sola vez)
│   └── modules/
│       ├── red/               #   VPC, subredes, IGW, NAT, tablas de ruteo, VPC Endpoints
│       ├── cluster/           #   EKS, grupo de nodos, AWS Load Balancer Controller
│       ├── imagenes/          #   Repositorios ECR y construcción de imágenes
│       ├── datos/             #   RDS y ElastiCache (Multi-AZ), DynamoDB, SQS y permisos IAM
│       └── aplicacion/        #   Microservicios, Ingress (ALB) y NetworkPolicies
├── the-store/                 # Código fuente de la aplicación (provisto por la cátedra)
├── verificar.sh               # Pruebas automáticas del entorno desplegado
└── docs/
    ├── preentrega.pdf         # Documento de pre-entrega (fuente: preentrega.tex / .md)
    ├── decisiones.md          # Decisiones de diseño y alternativas descartadas
    ├── guia-terraform.md      # Guía de lectura del código para el grupo
    ├── presentacion.md        # Guion de la presentación final y de la demo
    ├── resumen-clases.md      # Resumen de las clases teóricas
    └── img/arquitectura.*     # Diagrama de arquitectura
```

## Requisitos

| Herramienta | Versión | Para qué |
|---|---|---|
| Cuenta de AWS | - | Permisos para crear VPC, EKS, IAM (roles y políticas), ECR, RDS, ElastiCache, DynamoDB, SQS y S3 (es un POC: administrador) |
| AWS CLI | v2 | Credenciales, `aws eks get-token` (lo usan los providers de Kubernetes y Helm) |
| Terraform | >= 1.10 | Todo |
| Docker | 24+ | Construir las imágenes de los microservicios y publicarlas en ECR |
| kubectl | 1.30+ | Opcional: inspeccionar el clúster; lo usa `verificar.sh` |

Configurar las credenciales una sola vez (región `us-east-1`, formato `json`):

```bash
aws configure
aws sts get-caller-identity     # tiene que responder con la cuenta
```

Hacen falta unos 5 GB libres en disco para las imágenes.

## Costos

El entorno encendido cuesta aproximadamente **USD 0,45 por hora** (≈ USD 11 por
día): plano de control de EKS (0,10), dos NAT Gateway (0,09 + tráfico), dos
nodos `t3.medium` (0,083), RDS MySQL + PostgreSQL `db.t3.micro` Multi-AZ
(0,068), ElastiCache `cache.t3.micro` × 2 (0,034), Application Load Balancer
(0,0225), VPC Endpoint de SQS en dos zonas (0,02). DynamoDB, SQS, ECR y S3
cuestan centavos. **Se destruye el entorno al terminar cada sesión de
trabajo**; volver a crearlo tarda ~30 minutos y queda idéntico.

Todos los recursos llevan las etiquetas `Project = the-store` y
`ManagedBy = terraform`: en la consola de facturación se puede filtrar el
gasto del TP, y con `Resource Groups > Tag Editor` se verifica que no quede
nada huérfano después de un `destroy`.

## Puesta en marcha

### 0. Bucket del estado (una sola vez por cuenta)

El estado de Terraform se guarda en S3 para que los tres trabajemos sobre el
mismo entorno. El bucket se crea con la configuración de `bootstrap/`; el
nombre tiene que ser único en todo AWS:

```bash
cd terraform/bootstrap
terraform init
terraform apply -var bucket_name=the-store-tfstate-<apellido>
cd ..
```

Poner ese nombre en `terraform/backend.tf` (`bucket = "..."`) y commitearlo.

### 1. Crear el entorno

```bash
cd terraform
terraform init          # descarga providers y módulos, conecta con el bucket
terraform plan          # muestra qué va a crear (≈ 90 recursos), no toca nada
terraform apply         # pide confirmación ("yes") y crea todo
```

El `apply` tarda **unos 30 minutos**: EKS (~12 min) y RDS Multi-AZ (~15 min) se
crean en paralelo mientras Docker construye las cinco imágenes en la máquina (~10 min la
primera vez, segundos después gracias al cache) y las publica en ECR; al final
Helm instala el AWS Load Balancer Controller, que crea el ALB a partir del
Ingress de la aplicación.

### 2. Usar y verificar la tienda

```bash
terraform output url            # http://<nombre-del-balanceador>.elb.amazonaws.com
cd .. && ./verificar.sh         # 14 verificaciones automáticas
```

El nombre DNS del balanceador tarda 2 o 3 minutos en propagarse después del
`apply`; si el navegador no resuelve, esperar y reintentar.

Para inspeccionar el clúster con `kubectl`:

```bash
$(terraform -chdir=terraform output -raw kubeconfig_command)
kubectl get nodes -o wide
kubectl get pods -n the-store -o wide
kubectl get networkpolicies -n the-store
```

### 3. Destruir el entorno

```bash
cd terraform
terraform destroy       # ≈ 15 minutos; pide confirmación
```

Si el destroy falla a mitad de camino (lo más común: la VPC no se puede borrar
porque el ALB que creó el controlador tardó en desaparecer), volver a
ejecutarlo: Terraform retoma donde quedó. Si el Ingress queda "colgado" al
borrarse es porque el controlador ya no corre: reinstalarlo (`terraform apply
-target=module.cluster`) o borrar el ALB a mano y quitarle el *finalizer* al
Ingress con `kubectl patch`. El bucket del estado no se borra;
cuesta centavos y conserva el historial.

## Casos de uso (los de la pre-entrega)

Todos siguen el mismo ciclo: editar `terraform/terraform.tfvars`, revisar con
`terraform plan`, aplicar con `terraform apply`.

**1. Entorno reproducible y detección de desvíos (drift).** Los pasos 1 y 3 de arriba.
Para el drift, modificar algo por fuera de Terraform y ver cómo lo detecta y lo
corrige:

```bash
kubectl scale deployment ui -n the-store --replicas=1   # cambio "a mano"
terraform plan       # muestra: replicas 1 -> 2 (lo declarado)
terraform apply      # lo vuelve a dejar como está declarado
```

**2. Capacidad extra para una campaña de ventas.** En `terraform.tfvars` cambiar
`ui = 2` por `ui = 4` dentro de `replicas`, y `node_count = 2` por
`node_count = 3`. `terraform plan` muestra dos cambios (el Deployment de la UI
y el grupo de nodos); `terraform apply` lanza una instancia EC2 nueva (~3 min)
y levanta las dos réplicas adicionales. Volver a los valores originales y
aplicar de nuevo achica el clúster.

**3. Nueva versión de la aplicación y vuelta atrás.** Cambiar `app_version = "1.0"` por
`"1.1"` (para que el cambio se note a simple vista, modificar antes algún
texto en `the-store/src/ui`). `terraform apply` reconstruye las imágenes, las
publica en ECR con el tag nuevo y Kubernetes hace el *rolling update*: los pods
viejos se reemplazan de a uno sin cortar el servicio (verlo con `kubectl
rollout status deployment/ui -n the-store`). Para el rollback, volver a
`"1.0"` y aplicar de nuevo. Un cambio de configuración sin reconstruir nada,
por ejemplo `ui_theme = "orange"`, sigue el mismo camino.

**4. Contención de un microservicio comprometido.** Cambiar `quarantine = []` por
`quarantine = ["checkout"]`. `terraform plan` muestra un único cambio (la
etiqueta `tier` de los pods de checkout pasa a `cuarentena`) y, aplicado, el
servicio queda aislado: no recibe pedidos de la UI ni puede iniciar
conexiones. Se comprueba desde la tienda (el catálogo y el carrito funcionan;
el checkout da error) y desde adentro:

```bash
kubectl exec -n the-store deploy/ui -- curl -s -m 3 http://checkout/health   # timeout
kubectl exec -n the-store deploy/checkout -- curl -s -m 3 http://orders/     # timeout
```

Con `quarantine = []` y otro `apply` se levanta la cuarentena.

## Comandos útiles

```bash
terraform output                       # URL, endpoints, bloques de red, imágenes
terraform state list                   # todos los recursos administrados
terraform state show module.red.aws_vpc.this
terraform plan -destroy                # qué borraría un destroy, sin borrar
aws ec2 describe-instances --filters Name=tag:Project,Values=the-store \
  --query 'Reservations[].Instances[].[InstanceId,State.Name,PrivateIpAddress]' --output table
```

## Problemas conocidos

- **`aws eks get-token` / credenciales vencidas**: si las credenciales son
  temporales (SSO), renovarlas antes de cada `plan`/`apply`.
- **Versión de Kubernetes no disponible**: si AWS retiró la versión declarada
  en `kubernetes_version`, elegir una de `aws eks describe-cluster-versions
  --query 'clusterVersions[].clusterVersion'`.
- **El bucket ya existe**: el nombre de S3 es global; elegir otro en el
  bootstrap y en `backend.tf`. Después de cambiar `backend.tf` hay que correr
  `terraform init -reconfigure`.
- **Construcción de imágenes lenta o sin memoria**: Docker necesita ~4 GB de RAM
  para compilar los servicios Java. Sólo la primera vez tarda ~10 minutos.
- **`terraform destroy` se queda esperando el namespace o la VPC**: interrumpir
  con Ctrl+C una vez, esperar un minuto (el balanceador tarda en borrarse) y
  volver a ejecutar `terraform destroy`.

## Documentación

- [`docs/preentrega.pdf`](docs/preentrega.pdf): pre-entrega (contexto, diseño,
  scope, casos de uso, diagrama, alternativas).
- [`docs/decisiones.md`](docs/decisiones.md): todas las decisiones de diseño y
  las alternativas descartadas, con sus razones.
- [`docs/guia-terraform.md`](docs/guia-terraform.md): por dónde empezar a leer
  el código si nunca se usó Terraform.
- [`docs/presentacion.md`](docs/presentacion.md): estructura de la presentación
  final y guion de la demo.
