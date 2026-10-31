# T00 — Contrato de implementación EC2 + kind

Decisión de implementación del 31/10/2026. Fuente: [preentrega vigente](preentrega-vigente.pdf). Reemplaza las alternativas abiertas del plan. Los tres frentes implementan contra este contrato; los cambios de interfaz deben actualizar este archivo y sus consumidores en el mismo commit.

## Configuración y límites

`config/entorno.json` es la fuente compartida de direccionamiento, nombres, puertos, servicios y claves de estado. No contiene credenciales. `a` y `b` identifican clústeres independientes; los consumers usan mapas con esas claves, sin depender del orden arbitrario de outputs.

Cada EC2 ejecuta un control plane y un worker kind; ambos comparten recursos del host. Cada clúster tiene diez pods de aplicación en baseline, doce durante la campaña. Escalar UI no agrega EC2 ni recursos físicos. Las bases, la tabla y la cola son compartidas. No hay enrutamiento de pods/Services entre clústeres.

Camino: ALB HTTP/80 → EC2 TCP/8080 → kind containerPort 30080 → UI NodePort 30080 → pod TCP/8080. API de kind en loopback:6443. El operador llega por SSM y usa localhost:16443 para `a` y localhost:26443 para `b`, validando TLS con las CA/certificados de cada clúster. Los permisos reales de SSM y la capacidad se verifican en T01/T03/T04.

CNI elegido: Calico, deshabilitando kindnet y configurando el pool de pods con el CIDR compartido. La combinación concreta de versiones se registra en T01. No hay EKS, IRSA, nuevos roles IAM, nginx ni AWS LBC en el camino nuevo.

## Configuraciones Terraform y propiedad

| Configuración | Contenido y responsable | Estado |
|---|---|---|
| `terraform/bootstrap` | Bucket S3; A | Local protegido, conservado fuera de Git |
| `terraform/infra` | Red, SG, EC2, ALB y datos; A/B integran | `state_keys.infra` |
| `terraform/imagenes` | Repositorios y publicación inmutable; C | `state_keys.imagenes` |
| `terraform/aplicacion` | Objetos de los dos kind; C/B integran | `state_keys.aplicacion` |

Las tres raíces usan backend S3 parcial con cifrado y bloqueo nativo, configurado al inicializar con un archivo local. Se registran locks de providers por raíz. Ninguna raíz depende del estado histórico `the-store/terraform.tfstate`.

`terraform/` conserva temporalmente la implementación EKS anterior. **No ejecutar su apply/destroy como parte del flujo kind.** No mover recursos de tipo EKS a EC2 mediante state mv ni conectar la raíz nueva al estado viejo. Las carpetas futuras de imágenes/app se crean cuando tengan implementación; una carpeta vacía no se considera una fase disponible.

## Firmas entre módulos

- **red (A):** conserva `name`, `region`, `cidr`, `azs`, `public_subnets`, `private_subnets`, `db_subnets`. Agrega un modo explícito `create_application_security_groups = true` para el camino kind. Crea los SG EC2/ALB dentro de red; así datos, cómputo y ALB consumen IDs sin crear ciclos. El modo anterior se conserva para no cambiar de manera implícita el legacy EKS.
- **red → infra:** IDs de VPC, públicas/privadas/datos, tablas privadas y NAT; IDs de SG de aplicación/ALB/endpoints. La raíz transforma listas del módulo existente a mapas `a`/`b` mediante las AZ del contrato.
- **computo (B, T03):** recibe `private_subnet_ids = map(string)`, `application_security_group_id`, nombre del perfil existente y configuración kind. Devuelve `instance_ids = map(string)` e IP privadas con claves `a`/`b`. No crea/adjunta políticas a LabRole.
- **datos (A, T06):** recibe SG EC2 y subredes de datos. Conserva `connection` sensible con `mysql_host`, `mysql_password`, `postgres_host`, `postgres_password`, `redis_host`, `dynamodb_table`, `sqs_queue_url`. No se escriben contraseñas en tfvars ni se imprimen outputs sensibles.
- **ALB (A, T05):** target group tipo instance:8080; attachments consumen `instance_ids`. Health check `/actuator/health/readiness`. DNS sale del recurso AWS, no de un Ingress.
- **imagenes (C, T07):** repositorios por las cinco claves de `services`; publica versiones amd64 inmutables desde el equipo del grupo. Devuelve referencias por versión/servicio con digest registrado. Publicar y elegir `app_version` son operaciones separadas.
- **aplicacion (C, T08/T09):** dos instancias del mismo módulo con aliases Kubernetes **`kind_a`** y **`kind_b`**, uno por kubeconfig/túnel. Reciben el mismo `app_version`, `replicas` y `quarantine`. UI NodePort; backends ClusterIP. No configura providers dentro del módulo hijo.

T04 implementa el acceso mediante `python3 scripts/acceso.py run -- COMANDO ...`. Exporta `TF_VAR_access_manifest` para la raíz aplicación, abre/verifica ambos túneles y retira sesiones/certificados al terminar. `access_manifest` es obligatorio y temporal; no persiste credenciales en Terraform. Ambos aliases dependen de la comprobación conjunta y de un plugin local de certificados que también protege planes guardados. `enable_access_probe` (false por defecto) solo habilita los objetos de prueba T04. Ver [operación y pruebas](acceso-t04.md).

Interfaz pública estable de la raíz infra: `network` (VPC, subredes/tabla por `a`/`b`, NAT por zona y SG). T03 agrega `compute` (IDs/IP por zona), T05 `url` y `load_balancer` (ARN/DNS/listener/target group/IDs por a-b), y T06 `databases` (sensible) y `database_endpoints` (sin contraseñas). No devolver IDs ficticios para recursos todavía no implementados. T08 debe exponer `/actuator/health/readiness` HTTP/200 en UI:8080 y NodePort 30080 para el health check del ALB; ver [T05](alb-t05.md).

## Despliegue, versiones y cuarentena

1. Renovar la sesión del Lab y ejecutar preflight. Inventariar recursos/estado existentes.
2. Crear una vez el bucket o reutilizar uno del grupo comprobado; inicializar cada raíz con una key distinta.
3. Publicar v1/v2 en la raíz imágenes; crear infraestructura AWS y esperar bootstrap. Imágenes e infra no requieren APIs Kubernetes para planearse.
4. Establecer túneles y kubeconfigs privados; verificar identidad de cada clúster.
5. Aplicar app: EC2 descarga con LabRole y precarga imágenes en containerd de todos sus nodos kind antes del rollout. Autenticar Docker en el host no es autenticar Cart/Orders dentro de un pod: ambas vías se prueban.
6. Los tres casos de modificación se operan desde `terraform/aplicacion/terraform.tfvars` y afectan a ambos kind: réplicas UI, versión existente y policies de cuarentena. El cambio de versión nunca compila/publica; cuarentena cambia policies, no PodTemplate.
7. Destruir app de ambos kind mientras existen EC2 y acceso. Luego infra y, cuando corresponda, imágenes. Conservar bucket/estado y los recursos IAM preexistentes.

## Inventario y migración

En el checkout original no se encontraron archivos tfstate locales bajo terraform al iniciar T00. Eso **no demuestra** que la cuenta o el backend remoto estén vacíos. El backend histórico contiene un nombre CAMBIAR; no se consultó ni se migró un estado remoto con ese valor.

Con credenciales válidas: inventariar recursos con tags/IDs, comprobar el estado real que usa el grupo y guardar copia privada antes de cualquier migración. El cambio de privadas /20→/24 puede requerir reemplazos. El plan nuevo no se aplica hasta revisar ese impacto. No importar recursos que ya administra otro estado.

## Responsables y cierre de T00

A modifica red/datos/bootstrap; B cómputo/acceso y conexiones entre raíces; C imágenes/app/policies. Cada frente incluye sus pruebas; un solo operador realiza apply sobre el entorno compartido. T00 queda implementada mediante este contrato y la configuración compartida. No certifica las comprobaciones AWS pendientes de T01/T02.
