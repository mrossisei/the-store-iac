<p align="center">
  <img src="docs/img/banner.svg" alt="The Store: microservicios declarados con Terraform sobre AWS y dos clústeres kind" width="100%">
</p>

<p align="center">
  <img alt="Terraform 1.10 o superior" src="https://img.shields.io/badge/Terraform-%E2%89%A5%201.10-123F7E?logo=terraform&logoColor=white">
  <img alt="AWS us-east-1" src="https://img.shields.io/badge/AWS-us--east--1-123F7E?logo=amazonwebservices&logoColor=white">
  <img alt="kind 0.33" src="https://img.shields.io/badge/kind-0.33-123F7E?logo=kubernetes&logoColor=white">
  <img alt="Kubernetes 1.37" src="https://img.shields.io/badge/Kubernetes-1.37-123F7E?logo=kubernetes&logoColor=white">
  <img alt="Calico 3.33" src="https://img.shields.io/badge/Calico-3.33-123F7E">
</p>

<p align="center">
  <a href="#arquitectura">Arquitectura</a> &nbsp;|&nbsp;
  <a href="#organización-del-código">Código</a> &nbsp;|&nbsp;
  <a href="#cómo-levantar-el-entorno">Cómo levantarlo</a> &nbsp;|&nbsp;
  <a href="#casos-de-uso">Casos de uso</a> &nbsp;|&nbsp;
  <a href="#destruir-el-entorno">Destruir</a>
</p>

The Store es una tienda online de cinco microservicios. Este repositorio la despliega en AWS solo con Terraform: `plan`, `apply` y `destroy`.

Terraform crea la red, el Application Load Balancer, las imágenes en ECR, dos EC2 privadas, los servicios de datos y los objetos de Kubernetes. Cada EC2 ejecuta su propio clúster kind con dos réplicas de cada servicio: **20 pods de aplicación en total**.

**Grupo 2:** Matías Rossi, Juan Pablo Birsa y Federico Viera. Trabajo Práctico Especial de 72.20 Redes de Información, ITBA, 2C 2026.

## Arquitectura

<p align="center">
  <img src="docs/img/arquitectura.svg" alt="Diagrama: Internet llega al ALB por HTTP 80, que reparte a una EC2 privada por zona en el puerto 8080. Cada EC2 ejecuta un kind con UI, Catalog, Carts, Checkout y Orders. Las bases viven en subredes de datos sin salida a Internet." width="100%">
</p>

Un pedido entra por el ALB en HTTP 80 y llega al puerto 8080 de una EC2. El mapeo de puertos de kind lo pasa al NodePort 30080 de la UI, que lo entrega a un pod.

La UI llama a Catalog, Carts y Checkout, y Checkout llama a Orders. No hay otros caminos entre pods: las NetworkPolicies bloquean todo lo demás.

| Bloque | Uso |
|---|---|
| `10.0.0.0/16` | VPC |
| `10.0.1.0/24`, `10.0.2.0/24` | Subredes públicas: ALB y NAT Gateway de cada zona |
| `10.0.16.0/24`, `10.0.32.0/24` | Subredes privadas: EC2 con kind e interfaces del endpoint de SQS |
| `10.0.48.0/24`, `10.0.49.0/24` | Subredes de datos: RDS y ElastiCache, solo con la ruta local |
| `10.244.0.0/16` | Pods, interna de cada kind |
| `172.20.0.0/16` | Services, interna de cada kind |

Los dos clústeres son independientes: no comparten plano de control ni mueven pods entre EC2. Las réplicas de un kind comparten CPU y memoria de su host, así que no toleran la caída de esa instancia. La tolerancia entre zonas viene de tener una copia completa por zona, detrás del ALB.

## Organización del código

```text
terraform/
├── main.tf            Une los módulos
├── variables.tf
├── terraform.tfvars   Valores del entorno y de los casos de uso
├── outputs.tf
├── providers.tf
├── tests/
└── modules/
    ├── red/           VPC, subredes, NAT, endpoints, security groups y ALB
    ├── computo/       EC2 y preparación de Docker, kind y Calico
    ├── imagenes/      Repositorios ECR, construcción y publicación
    ├── datos/         RDS, ElastiCache, DynamoDB y SQS
    └── aplicacion/    Deployments, Services, Secret y NetworkPolicies
scripts/acceso-kind.sh Túneles SSM a kind; lo ejecuta Terraform
the-store/             Código de la aplicación
```

Hay una sola configuración de Terraform, con un estado. `main.tf` usa `modules/aplicacion` dos veces, una por kind.

### Cómo se conecta todo

- **Imágenes:** el provider `docker` construye `linux/amd64` en tu equipo y publica v1 y v2 en ECR, con tags inmutables.
- **Descarga:** cada EC2 obtiene un token de ECR con LabRole y lo renueva con un timer. Los nodos kind lo usan para descargar las imágenes.
- **Acceso:** las EC2 son privadas. En cada `plan` y `apply`, Terraform ejecuta `acceso-kind.sh`, que espera a que kind esté listo y abre un túnel SSM a cada API.

El script consulta la API de cada kind cada 30 segundos para que los túneles SSM no venzan por inactividad durante la construcción de imágenes o la espera de las bases. En cada ejecución reabre los túneles cerrados y comprueba que el kubeconfig corresponda a la EC2 actual.

## Cómo levantar el entorno

### Requisitos

Terraform 1.10 o superior, AWS CLI, Session Manager plugin, kubectl y Docker en la máquina que ejecuta Terraform, porque compila las imágenes.

En Windows, corré todo en WSL con la integración de Docker Desktop activada. La sesión del Learner Lab tiene que estar vigente.

> [!CAUTION]
> Los estados de Terraform contienen las contraseñas de las bases. `.local/` guarda los kubeconfigs: mantenela privada y fuera de Git.

### Una sola vez

El bucket del estado es lo único fuera de Terraform: tiene que existir antes de guardar el estado en él. S3 lo cifra por defecto.

```bash
export STATE_BUCKET=the-store-tfstate-CUENTA-us-east-1

aws s3api create-bucket --bucket "$STATE_BUCKET" --region us-east-1
aws s3api put-bucket-versioning --bucket "$STATE_BUCKET" --versioning-configuration Status=Enabled

cd terraform
terraform init -backend-config="bucket=$STATE_BUCKET"
```

### Levantar

```bash
terraform plan
terraform apply
terraform output url
```

`apply` construye las diez imágenes, crea la infraestructura, espera a que kind esté listo en ambas EC2 y despliega la aplicación. Tarda varios minutos.

## Casos de uso

Salvo el primero, cada caso consiste en cambiar un valor en `terraform/terraform.tfvars` y ejecutar `terraform plan` y `terraform apply`. Los cambios afectan a ambos kind.

| Caso | Qué se cambia | Qué se comprueba |
|---|---|---|
| **Drift** | Un recurso desde la consola de AWS | `plan` detecta el desvío y `apply` lo corrige |
| **Campaña de ventas** | `replicas.ui` de 2 a 4 y de vuelta a 2 | 20, 24 y 20 pods, con las mismas dos EC2 |
| **Nueva versión** | `app_version` de `"v1"` a `"v2"` y de vuelta | Rolling update y rollback sin reconstruir |
| **Servicio comprometido** | `quarantine = ["checkout"]` y luego `[]` | Solo cambian NetworkPolicies; catálogo y carrito siguen andando |

Para mirar los pods de un clúster:

```bash
kubectl --kubeconfig ../.local/kind-a.kubeconfig get pods -n the-store
```

## Destruir el entorno

```bash
terraform destroy
```

Terraform destruye primero los objetos de ambos kind y después la infraestructura, porque la aplicación depende de las EC2.

Después verificá en AWS que no queden recursos del proyecto. El bucket del estado se conserva a propósito.

## Alcance

Quedan fuera del POC: EKS, TLS, integración continua, observabilidad, autoescalado y permisos IAM separados por microservicio.

Conectar la aplicación a bases reales mostró dos errores en el código original. Se corrigieron para que la compra guarde datos correctos:

- **Checkout** enviaba a Orders la dirección y los precios con un formato incorrecto.
- **Orders** guardaba el identificador de cada producto como un índice de lista.

Además, los Dockerfiles registran la versión de cada imagen y la UI la muestra.
