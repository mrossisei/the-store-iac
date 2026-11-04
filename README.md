# The Store — Terraform, AWS y dos clústeres kind

Trabajo Práctico Especial de Redes de Información, ITBA, 2C 2026. Integrantes: Matías Rossi, Juan Pablo Birsa y Federico Viera.

El alcance vigente es la [preentrega EC2 + kind](docs/preentrega-vigente.pdf). Terraform administra la red AWS, dos EC2 privadas con un kind independiente por AZ, ALB y servicios de datos compartidos. Cada kind aloja dos réplicas de UI, Catalog, Carts, Checkout y Orders: **20 pods de aplicación en total**. UI puede escalar a cuatro réplicas por kind sin agregar EC2 ni nodos.

**Estado y evidencia:** consultar [estado de tareas](docs/estado-tareas.md), [plan](docs/plan-de-trabajo.md) y [mapa](docs/mapa-de-tareas.html). T08/T09 tienen pruebas reales de aplicación, compras por API y cuarentena. T11/T12 están en ejecución sobre una sola sesión AWS. GitHub Actions (T15) está pospuesta; el procedimiento operativo actual es local. El PPT es un borrador que distingue pruebas aprobadas de pendientes.

## Arquitectura y propiedad

```text
Navegador → ALB HTTP:80
              ├─ EC2 privada AZ a:8080 → kind a → NodePort UI:30080 → pod:8080
              └─ EC2 privada AZ b:8080 → kind b → NodePort UI:30080 → pod:8080

Cada kind: UI + Catalog + Carts + Checkout + Orders, dos réplicas por servicio.
Datos compartidos: MySQL, PostgreSQL, Redis, DynamoDB y SQS.
Administración: operador → SSM → API privada de cada kind, con TLS.
```

Los clústeres no comparten plano de control ni reprograman pods entre EC2. Los nodos kind de cada host comparten su memoria/CPU. Las subredes AWS son /24; los CIDR de pods y Services son internos de cada kind. Ver [contrato](docs/contrato-implementacion.md) y [red/estado](docs/operacion-estado-red.md).

| Raíz | Administra | Estado |
|---|---|---|
| `terraform/bootstrap` | Bucket y controles de estado | Local privado, conservado fuera de Git |
| `terraform/infra` | Red, dos EC2, ALB y datos | S3: `state_keys.infra` |
| `terraform/imagenes` | Cinco repositorios ECR inmutables | S3: `state_keys.imagenes` |
| `terraform/aplicacion` | Aplicación y policies en ambos kind | S3: `state_keys.aplicacion` |

`config/entorno.json` define nombres, redes, puertos y claves S3; `config/herramientas.json` fija las versiones. **La raíz histórica `terraform/` corresponde a EKS: no ejecutar su apply/destroy para este POC.** No requiere EKS, Ingress Controller ni nuevos roles IAM; reutiliza LabRole/LabInstanceProfile.

## Preparar el operador y los estados

Se necesitan Terraform >=1.10, AWS CLI, Python 3, kubectl, jq y Session Manager plugin. Docker/buildx se necesitan para publicar artefactos; las pruebas locales kind también requieren Docker/kind. Usar las versiones del contrato y las [comprobaciones T01](docs/ejecucion-t01.md).

1. Renovar la sesión del Learner Lab en el perfil AWS del operador, sin copiar claves a Git, tfvars o pods. Verificar `aws sts get-caller-identity --query Account --output text`.
2. Identificar el bucket existente del grupo y comprobar su propiedad/estado. No crear otro backend para ocultar un error de permisos o la desaparición de un bucket. El bootstrap inicial y su recuperación se explican en [T02](docs/operacion-estado-red.md).
3. Inicializar las tres raíces contra ese mismo bucket y las claves diferentes del contrato:

```bash
export TP_STATE_BUCKET=the-store-tfstate-CUENTA-us-east-1  # reemplazar por el bucket real
python3 scripts/estado.py init infra --bucket "$TP_STATE_BUCKET"
python3 scripts/estado.py init imagenes --bucket "$TP_STATE_BUCKET"
python3 scripts/estado.py init aplicacion --bucket "$TP_STATE_BUCKET"
```

Los estados/planes contienen datos sensibles. Mantener `.local/` privada y fuera de Git; no imprimir estados ni subir planes binarios/JSON como evidencia. No modificar el kubeconfig global del operador.

## Levantar una vez y conservar para las pruebas

Confirmar primero que existen las publicaciones ECR y sus digests. `terraform/imagenes/releases-aplicacion.json` selecciona los artefactos de aplicación, incluidas las correcciones inmutables de Checkout/Orders. La selección v1/v2 no construye ni publica imágenes. Si hubo un reset del Lab, seguir la recuperación de [T07](docs/imagenes-t07.md) y [T08](docs/aplicacion-t08.md); un runner o equipo limpio no tiene las copias Docker locales necesarias para restaurarlas.

```bash
umask 077
mkdir -p .local/operacion
terraform -chdir=terraform/infra plan -input=false -out=../../.local/operacion/infra.tfplan
# Revisar el alcance antes de aplicar; no aceptar bajas/reemplazos inesperados.
terraform -chdir=terraform/infra apply -input=false ../../.local/operacion/infra.tfplan

# Esperar y verificar el bootstrap de ambas EC2 antes de desplegar la app.
python3 scripts/verificar-computo.py --report .local/operacion/computo.json
python3 scripts/aplicacion.py apply
terraform -chdir=terraform/infra output -raw url
```

`verificar-computo.py` realiza su comprobación de repetición del servicio de bootstrap; ejecutarla antes de aplicar la app. No usar su opción de reboot en medio de una campaña sin coordinarlo. Ver [T03](docs/computo-t03.md).

`aplicacion.py apply` abre y valida ambos túneles, precarga los digests en los cuatro nodos con LabRole, revisa el plan y lo aplica en la misma sesión. Al terminar retira los accesos temporales; las EC2 y la aplicación permanecen. Un plan de app guardado no se reutiliza después de cerrar su sesión. Ver [T04](docs/acceso-t04.md), [T08](docs/aplicacion-t08.md) y [T09](docs/politicas-t09.md).

## Pruebas y cuatro casos

Conservar el mismo entorno entre integración y campañas. Un solo operador modifica los estados compartidos; los demás pueden preparar código/documentación en worktrees aislados.

- **T11:** ambas copias y ALB, compras por navegador, orden/evento SQS nuevos y persistencia al recrear pods. Preparación de Cypress, configuración explícita por clúster y ejecución en [T10](docs/verificacion-t10.md).
- **Drift AWS:** cambiar un recurso propio permitido, comprobar el plan, corregir con apply y volver a convergencia.
- **Réplicas:** editar `replicas.ui` en `terraform/aplicacion/terraform.tfvars`, 2→4→2 por kind; 20→24→20 pods app y dos EC2 constantes.
- **Versión:** `app_version` v1→v2→v1 con publicaciones existentes, precarga y rollout/rollback. No reconstruir tags.
- **Cuarentena:** `quarantine = ["checkout"]` y luego `[]`; solo cambian policies. Probar PodIP, DNS, datos e Internet, catálogo/carrito sanos y UID/restarts estables con [las sondas T09](docs/politicas-t09.md).

Para inspeccionar Kubernetes, usar una sesión explícita de [T04](docs/acceso-t04.md):

```bash
python3 scripts/acceso.py run -- bash
# Dentro: THE_STORE_ACCESS_MANIFEST identifica kubeconfigs/contextos privados de a/b.
# Usar esos destinos explícitos; exit cierra ambos accesos.
```

Para un plan de app de solo lectura, usar `acceso.py run -- terraform -chdir=terraform/aplicacion plan -input=false` con la versión ya precargada. `aplicacion.py plan` también prepara imágenes y no constituye una operación de solo lectura estricta. Las guías enlazadas describen los reportes y precondiciones; no aceptar un timeout causado por DNS, herramienta ausente o API inaccesible como prueba de aislamiento.

## Cerrar la sesión

Retirar **aplicación antes que infraestructura**, con ambos kind todavía accesibles. No hacer destroy entre casos de prueba.

```bash
python3 scripts/aplicacion.py destroy
terraform -chdir=terraform/aplicacion state list  # debe quedar vacío
terraform -chdir=terraform/infra plan -destroy -input=false -out=../../.local/operacion/infra-destroy.tfplan
# Revisar el plan y los IDs propios para la auditoría.
terraform -chdir=terraform/infra apply -input=false ../../.local/operacion/infra-destroy.tfplan
terraform -chdir=terraform/infra state list       # debe quedar vacío
```

Auditar en AWS los recursos por IDs/tags: ALB/targets, EC2/EBS, NAT/EIP, VPC/ENI/SG/endpoints y datos. Conservar intencionalmente bucket/versiones de estado, ECR con sus imágenes y LabRole/LabInstanceProfile preexistentes. No destruir bootstrap ni ECR como limpieza rutinaria. La persistencia se exige ante reinicios de pods; destruir infra elimina las bases y la cola. La recreación formal se registra separadamente de la limpieza, con evidencia de cada fase.

## Documentación y entrega

- [Datos T06](docs/datos-t06.md), [ALB T05](docs/alb-t05.md), [aplicación T08](docs/aplicacion-t08.md), [políticas T09](docs/politicas-t09.md).
- [PPT editable](docs/entrega/presentacion.pptx), [PDF](docs/entrega/presentacion.pdf), [guion](docs/presentacion.md) y [referencia de formato](docs/referencia-presentacion-t14.md). Borrador pendiente de evidencia final y ensayo.
- [Diseño de GitHub Actions T15](docs/automatizacion-t15.md), pospuesto por prioridad de entrega. No hay workflows operativos ni secrets configurados por esta documentación.

Las afirmaciones de cierre y las limitaciones de las pruebas están en [estado-tareas.md](docs/estado-tareas.md). Los documentos históricos de EKS se conservan en Git; usar la preentrega vigente y las guías EC2 + kind para operar.
