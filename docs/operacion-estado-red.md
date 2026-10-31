# T02 — Estado remoto y red kind

La raíz nueva es **terraform/infra**, independiente del estado EKS histórico. La fuente de parámetros es config/entorno.json. T02 implementa red/SG; T03 agregó las EC2 privadas y su bootstrap, documentados en [computo-t03.md](computo-t03.md). ALB y datos se agregan en T05/T06.

## Inicializar

```bash
python3 scripts/preflight.py --report .local/preflight.json
terraform -chdir=terraform/bootstrap init
terraform -chdir=terraform/bootstrap plan -var bucket_name=NOMBRE_UNICO
terraform -chdir=terraform/bootstrap apply -var bucket_name=NOMBRE_UNICO
python3 scripts/estado.py init infra --bucket NOMBRE_UNICO
terraform -chdir=terraform/infra plan
terraform -chdir=terraform/infra apply
python3 scripts/verificar-red.py --bucket NOMBRE_UNICO
python3 scripts/probar-bloqueo.py --bucket NOMBRE_UNICO
```

NOMBRE_UNICO se elige para la cuenta; en la sesión se utilizó el patrón the-store-tfstate-CUENTA-us-east-1. No reemplazar el bucket si ya contiene el estado del grupo. La inicialización genera .local/infra.backend.hcl con key the-store/kind/infra.tfstate, encrypt=true y use_lockfile=true. No escribe credenciales. Imágenes y app tienen claves diferentes en el contrato; estado.py rechaza esas raíces mientras no estén implementadas.

El archivo terraform/bootstrap/terraform.tfstate es local y se conserva de forma privada para administrar controles del bucket; no se commitea. Guardar también una copia privada fuera del checkout. En esta sesión se conservó en ~/.local/state/the-store-iac/ con permisos 600. Las credenciales del perfil deben renovarse cuando expire la sesión del Lab.

## Compatibilidad de bootstrap con Academy

En esta cuenta, el SCP prohíbe s3:GetBucketObjectLockConfiguration. El provider AWS 6.66.0 consulta obligatoriamente esa API al leer aws_s3_bucket, incluso con Object Lock sin habilitar. Su código no ofrece un flag para omitirla; [lectura del provider](https://github.com/hashicorp/terraform-provider-aws/blob/v6.66.0/internal/service/s3/bucket.go). No confundir Object Lock (retención WORM) con el lockfile nativo de Terraform.

Por eso el bootstrap usa **terraform_data + scripts/bootstrap-bucket.py** para crear o verificar únicamente el contenedor S3 mediante AWS CLI. La adopción verifica dueño y etiquetas Project/ManagedBy; un 403 nunca se interpreta como bucket inexistente. Cifrado SSE-S3, versionado, acceso público bloqueado y policy que exige HTTPS siguen como recursos Terraform nativos. No se cambian permisos de IAM/SCP ni se debilitan controles.

El bootstrap tiene prevent_destroy y deliberadamente no borra el bucket. Como terraform_data no refresca la existencia del bucket como un recurso S3 nativo, si alguien borra ese bucket por fuera se debe revisar/restaurar el estado y ejecutar una recreación controlada de state_bucket; no se promete autocorrección transparente de ese caso. La prueba de drift del TP debe usar un recurso AWS de la raíz infra administrado nativamente, por ejemplo un tag o regla de SG.

La primera prueba creó el bucket, pero el read del recurso nativo falló por ese SCP. Se guardó copia privada del tfstate, se retiró **solo esa entrada fallida** del estado local y se adoptó el mismo bucket mediante el mecanismo nuevo. No se borró/recreó el bucket ni se importaron recursos de otro estado. Es una recuperación específica de esta sesión, no un paso que repetir en un entorno existente.

## Qué permite la red

- VPC de dos AZ; públicas 10.0.1.0/24 y 10.0.2.0/24, privadas 10.0.16.0/24 y 10.0.32.0/24, datos 10.0.48.0/24 y 10.0.49.0/24.
- Cada tabla privada sale por el NAT de su AZ. La tabla de datos tiene solo ruta local y asociaciones explícitas.
- Gateway endpoints S3/DynamoDB en las tablas privadas; SQS Interface con DNS privado en ambas privadas y 443 exclusivamente desde SG EC2 en modo kind.
- SG ALB recibe HTTP/80 público y solo sale a SG EC2:8080. SG EC2 solo recibe 8080 desde ALB. Su egreso permite instalación HTTP(S), DNS al resolver y los puertos MySQL/PostgreSQL/Redis hacia datos. El control de entrada a las bases se agrega en T06.
- No se abre SSH ni la API Kubernetes en los SG. SSM opera por salida HTTPS. Los hosts/pods todavía no existen en T02: no se certifica resolución DNS desde una EC2 ni conectividad de aplicación antes de T03/T08.

El módulo red conserva explícitamente su modo anterior (create_application_security_groups=false) para el consumidor EKS histórico. La raíz infra activa true. No aplicar la raíz legacy para continuar el camino kind.

## Pruebas y limpieza

```bash
python3 -m unittest discover -s tests -v
terraform fmt -check -recursive terraform
terraform -chdir=terraform/infra validate
terraform -chdir=terraform/infra test
terraform -chdir=terraform/bootstrap validate
terraform -chdir=terraform/bootstrap test
```

Los tests Terraform usan mock_provider; no crean recursos reales. Cubren NAT/rutas por AZ, seis subredes, aislamiento de datos, endpoints y referencias SG. verificar-red.py contrasta los recursos reales y los controles del bucket mediante las APIs AWS. No usar los mocks como reemplazo de esa comprobación.

probar-bloqueo.py crea su lock con If-None-Match para no pisar uno existente, comprueba que plan falla por estado bloqueado y retira solamente el lock cuyo ID le pertenece. No usa force-unlock. No ejecutarlo simultáneamente con operaciones de otro integrante.

Al cerrar la sesión de pruebas:

```bash
terraform -chdir=terraform/infra plan -destroy
terraform -chdir=terraform/infra destroy
terraform -chdir=terraform/infra state list
```

Conservar bucket y versiones del estado; auditar VPC/NAT/EIP/endpoints/ENI/SG para que no queden recursos facturables. Para continuar T03 se recrea infra con apply. Cuando haya app, destruirla primero con acceso a ambos kind y luego infra. Nunca ejecutar destroy de bootstrap como limpieza del POC.

## Evidencia del 31/10/2026

- Bootstrap real: cinco recursos gestionados (contenedor vía terraform_data y cuatro controles S3); segundo plan sin cambios.
- Infra real: 42 recursos creados. Las consultas verificaron seis subredes/CIDR/AZ, dos NAT disponibles con rutas propias, datos sin salida por defecto, tres endpoints disponibles, DNS privado de SQS y referencias SG/puertos.
- Bucket: SSE-S3 AES256, versionado Enabled, cuatro bloqueos de acceso público y policy HTTPS. Lock condicional S3 probado: otro plan fue rechazado por bloqueo y se retiró únicamente el lock propio.
- Segundo plan de infra: sin cambios. Pruebas locales: 12 tests Python, dos tests Terraform de red y uno de bootstrap; fmt/validate aprobados. La prueba kind/Calico está registrada en T01.
- Limpieza: plan revisado de eliminación exclusivamente de los 42 recursos de module.red; apply de ese plan completado. Estado infra vacío. Auditoría por los IDs creados: sin VPC, EIP, ENI, SG, subredes ni endpoints; NAT en deleted. Se conserva el bucket con sus versiones y el estado local privado de bootstrap.

Logs, planes y registros de IDs quedan en .local/ y no se versionan. No hay instancias ni pods de aplicación en esta evidencia: las pruebas de SSM T01 y la posterior integración tienen su alcance propio.
