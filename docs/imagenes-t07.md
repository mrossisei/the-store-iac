# T07 — Imágenes inmutables

La raíz `terraform/imagenes` administra exclusivamente cinco repositorios ECR (`the-store/ui`, `catalog`, `carts`, `orders`, `checkout`). Usa AWS provider 6.66.0 con lock registrado, S3 parcial, cifrado y bloqueo nativo. `config/entorno.json` define región, claves y correspondencia `carts` → carpeta `cart`. El módulo `ecr-repositories` es independiente del módulo legacy `imagenes`; no ejecutar la raíz legacy.

## Crear y publicar

Desde la raíz del repositorio, con Docker y sesión AWS local vigente:

```bash
python3 scripts/estado.py init imagenes --bucket the-store-tfstate-891200271122-us-east-1
terraform -chdir=terraform/imagenes plan -out=../../.local/imagenes.tfplan
terraform -chdir=terraform/imagenes apply ../../.local/imagenes.tfplan
python3 scripts/publicar-imagenes.py publish v1
python3 scripts/publicar-imagenes.py publish v2
```

El plan debe contener únicamente los cinco repositorios. Terraform no contiene recursos Docker, provisioners, builds ni acceso a Kubernetes. No crea IAM ni modifica infra. `force_delete=false` evita borrar accidentalmente repositorios con imágenes.

El publicador construye desde el código local para `linux/amd64`, carga al Docker local, comprueba arquitectura y publica con como máximo dos builds simultáneos (`--jobs 1` o `2`). No borra imágenes ni cachés. Los dos juegos tienen etiquetas OCI de versión diferentes; UI además incorpora `The Store · v1` o `The Store · v2` en `#store-version`, visible en la navegación del catálogo, carrito y checkout (la home tiene una navegación independiente). No hay cambios en operaciones de compra. Checkout corrige el propietario de COPY a `appuser:appuser`, que es el usuario existente en la etapa final.

Los repositorios son `IMMUTABLE`. El script rechaza tags existentes antes de construir. Tras cada push registra el digest retornado por ECR en `terraform/imagenes/releases.json`. La existencia de ese archivo puede representar una publicación parcial: sólo una versión con las cinco claves es seleccionable. `--resume` permite completar faltantes después de un fallo, únicamente si los tags existentes coinciden con el registro; nunca reescribe. Un push exitoso seguido de fallo antes del registro requiere recuperar/verificar el digest manualmente, no reconstruir ni borrar tags automáticamente. No editar digests para forzar selección.

La autenticación Docker usa `get-login-password` por stdin y un `DOCKER_CONFIG` temporal privado, retirado al terminar. No modifica `~/.docker`, no imprime tokens ni consulta archivos de credenciales. Logs de build/push en `.local/t07/VERSION-SERVICIO.log`, permisos 600; los errores de autenticación no se vuelcan a consola.

## Seleccionar sin publicar

```bash
python3 scripts/publicar-imagenes.py select v1 > .local/seleccion-v1.json
python3 scripts/publicar-imagenes.py select v2 > .local/seleccion-v2.json
python3 scripts/publicar-imagenes.py select v1 > .local/rollback-v1.json
cmp .local/seleccion-v1.json .local/rollback-v1.json
```

`select` consulta ECR, exige exactamente las cinco claves y valida digest/plataforma/repositorio. Emite `{app_version, images}` con referencias `repository@sha256:...`. No invoca Docker. Esta interfaz está destinada al consumidor T08: el módulo aplicación recibe `images`; la variable de aplicación `app_version` elige un juego registrado y no ejecuta el publicador.

La raíz imágenes también permite inspeccionar la selección, sin builds ni push:

```bash
terraform -chdir=terraform/imagenes plan \
  -var='release_manifest=releases.json' -var='app_version=v1'
```

`release_manifest` se resuelve respecto al directorio de Terraform. `repositories` devuelve mapa servicio→URL; `references` devuelve versión→servicio→registro; `images` devuelve el juego seleccionado por digest. Sin `app_version`, `images={}`. Un juego incompleto o digest distinto de ECR falla por precondición. Estos argumentos cambian outputs, no repositorios ni artefactos. La selección que finalmente consume T08 debe aplicar la misma validación y jamás construir/publicar desde un plan de app.

## Descarga independiente desde EC2

El padre entrega un JSON privado con `schema:1`, `status:"ready"`, `region:"us-east-1"`, `compute.instance_ids:{a:"i-...",b:"i-..."}`. También se admiten `hosts_ready`/`compute_ready` y la forma `compute:{a:{instance_id:"i-..."},b:{instance_id:"i-..."}}` entregada por T06. Si continúa en `preparing`, esta prueba sigue pendiente. `--generation` exige la generación coordinada; antes y después de cada RunCommand se vuelve a leer el archivo y se rechazan cambios de generación/IDs o estados no listos. La generación queda en la evidencia por host. Los pulls de una generación retirada no certifican sus reemplazos.

```bash
python3 scripts/probar-pull-imagenes.py \
  --coordination /home/juan/Documentos/FACULTAD/redes/.worktrees/t00-t02/.local/t06-t07-coordination.json \
  --generation 2
```

El script valida previamente ambos juegos contra ECR y ejecuta `scripts/ssm.py` RunCommand en cada host (ambos hosts en paralelo, pulls secuenciales por host). Un entorno vacío, archivos de configuración/credenciales `/dev/null` y HOME temporal obligan al AWS CLI remoto a obtener credenciales del perfil de instancia. Exige ARN `assumed-role/LabRole/` y misma cuenta que el registry. Hace diez `docker pull --platform linux/amd64 URL@digest` por host, verifica arquitectura y RepoDigests, y devuelve evidencia privada `.local/t07/pull-evidence.json` y logs a/b (600). No reinicia kind ni opera workloads. La precarga en containerd de todos los nodos kind y permisos AWS de pods corresponden a T08/T11.

## Verificación y limpieza coordinada

```bash
python3 -m unittest discover -s tests -p test_imagenes.py -v
terraform -chdir=terraform/imagenes fmt -check -recursive
terraform -chdir=terraform/imagenes validate
terraform -chdir=terraform/imagenes test
# Con ambos juegos publicados: ECR, selección Terraform y UI HTTP local en `/catalog`:
python3 scripts/probar-imagenes.py
```

Las pruebas reales y estado final se registran en el handoff privado del padre; no inferir pulls de EC2 a partir de permisos del publicador. Por coordinación T06/T07 se conservan intencionalmente ambos juegos ECR y su estado para T08; el padre retira sólo la infraestructura de prueba. No destruir ECR en este cierre. Para retirar después de la autorización coordinada: listar y borrar explícitamente sólo imágenes de estos cinco repositorios, luego revisar/aplicar `terraform -chdir=terraform/imagenes destroy`. No borrar bucket, estados ni IAM preexistentes. Los artefactos locales de Docker no se limpian automáticamente.

## Evidencia ejecutada — 31/10/2026

Se aplicó únicamente imágenes: cinco repositorios creados, sin cambios en otras raíces. Se publicaron los diez tags reales de `releases.json`, cada versión con los cinco servicios, arquitectura comprobada `linux/amd64` y digests distintos entre v1/v2. La sesión local publicó; ambas EC2 definitivas de generación 2 descargaron los diez digests cada una con identidad de instancia LabRole. El piloto de generación 1 no se cuenta como prueba de sus reemplazos.

Pasaron 47 pruebas unitarias (nueve T07), dos pruebas Terraform con provider mock, validate/fmt, tres planes reales v1→v2→v1 sin cambios de recursos, rechazos reales de selección incompleta/digest alterado y reescritura (`ImageTagAlreadyExistsException`). Ambas UI respondieron HTTP 200 en `/catalog` con su versión visible. El plan final por defecto terminó con código 0, sin cambios. No se reinició kind ni se operaron workloads.

Evidencias privadas en `.local/t07/publication-evidence.json`, `pull-evidence.json` (dos hosts, generación 2, diez referencias por host), `references-v1.json`, `references-v2.json` y logs de planes. El handoff privado del padre registra commit/rama y rutas absolutas. ECR y su estado permanecen intencionalmente retenidos para T08; la carga en containerd kind y el uso de LabRole dentro de pods siguen perteneciendo a T08/T11.

Referencias primarias consultadas: [inmutabilidad ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-tag-mutability.html), [publicación y login por stdin](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html), [permisos independientes ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/security_iam_id-based-policy-examples.html), [buildx: plataforma, load y provenance](https://docs.docker.com/reference/cli/docker/buildx/build/), [pull por digest](https://docs.docker.com/reference/cli/docker/image/pull/).
