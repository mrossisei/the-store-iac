# T08 — Aplicación en ambos kind

`terraform/aplicacion` usa los aliases de acceso T04 y dos instancias de `modules/aplicacion`, una por clúster. Cada una administra namespace, Secret SQL, cinco Deployments y cinco Services. El baseline tiene dos réplicas por servicio: diez pods por kind, veinte en total. UI expone NodePort 30080 y TCP8080; el bootstrap conecta el host8080 a ese NodePort y el ALB T05 apunta a ambas EC2. Los backends son ClusterIP. No hay Ingress, controlador AWS LBC ni distribución por AZ dentro de kind.

Las etiquetas de los pods son estables (`app`, `tier`). La variable `quarantine` no afecta a PodTemplate; las políticas T09 son independientes. Los rollouts permiten un pod adicional por Deployment y cero indisponibles configurados, con startup/readiness probes y recursos explícitos. La disponibilidad efectiva se verifica al operar y depende del margen físico del host.

## Configuración y datos

Editar `terraform/aplicacion/terraform.tfvars`: `app_version`, `replicas` y `quarantine` gobiernan simultáneamente ambos destinos. `enable_application=true` activa los microservicios; false permite ejecutar exclusivamente las sondas T04. `scripts/probar-terraform-kind.py` fuerza false y rechaza estados con aplicación real.

La raíz lee únicamente la key infra del bucket de estado. `state_bucket=null` reutiliza el bucket inicializado de su backend S3; se puede indicar explícitamente. Ambas copias reciben los mismos endpoints. Los passwords SQL van en Secret Kubernetes y referencias `secretKeyRef`; nunca en tfvars ni credenciales AWS estáticas. El estado y los planes Terraform contienen material sensible y se conservan privados/cifrados, aunque la consola oculte atributos sensibles.

Orders usa las propiedades planas definidas por `DatabaseProperties.java` (`RETAIL_ORDERS_PERSISTENCE_ENDPOINT/NAME/USERNAME/PASSWORD`); no confundirlas con el bloque histórico `postgres` del YAML. Cart y Orders usan la cadena de credenciales del SDK hacia IMDSv2/LabRole existente, sin IRSA ni roles nuevos. El hop limit 3 del host se comprueba desde los pods, no se da por probado porque EC2 pueda llamar AWS.

## Precarga por digest

`scripts/seleccionar-release.py` valida los cinco digests de `terraform/imagenes/releases-aplicacion.json` contra ECR usando la cuenta de la sesión actual. Solo selecciona una publicación existente: no invoca Docker/build/push.

`scripts/preparar-imagenes.py prepare --version v1` se ejecuta dentro de `acceso.py run`. En cada EC2 obtiene identidad y token ECR con el perfil de instancia LabRole. Descarga manifest/config/capas en un layout OCI, verifica SHA256 y linux/amd64 y conserva el manifest original sin reserializarlo. Importa el archivo en containerd de control plane y worker mediante `kind load image-archive`, y exige que CRI reconozca la referencia exacta `repository@digest` en los cuatro nodos. No se compila en EC2.

El password ECR permanece en memoria; no se incluye en RunCommand, argumentos de procesos ni ficheros Docker. Las redirecciones del blob se descargan sin reenviar su Authorization. Los archivos temporales se retiran; quedan blobs de imágenes en `/var/cache/the-store/images`, con checksums, y la caché de containerd hasta retirar los hosts. Cada host serializa operaciones con un lock.

`check-external`, usado por Terraform, es de solo lectura: verifica acceso/identidades y que todos los digests seleccionados ya están en ambos nodos de cada kind. Un plan no carga imágenes ni inicia builds. Cambiar `app_version` exige precargar primero esa publicación. `imagePullPolicy=IfNotPresent` permite usar los digests registrados en CRI sin credenciales personales ni un login de registry en Kubernetes.

## Correcciones de compra y persistencia

La compra real detectó que el cliente generado de Checkout serializaba una dirección plana y omitía `unitCost`, mientras Orders espera `shippingAddress` anidado y los precios por ítem. Se corrigió `HttpOrdersService.ts` para enviar el DTO esperado y rechazar respuestas HTTP fallidas. Dos pruebas Jest con `fetch` simulado comprueban el cuerpo enviado y el rechazo de errores. La sonda AWS verifica el recorrido real hasta PostgreSQL y SQS.

Los diez tags originales v1/v2 de T07 siguen inmutables en `releases.json`. `releases-aplicacion.json` conserva tres servicios originales y selecciona Checkout y Orders `v1-t08`/`v2-t08` por digest, dentro de sus repositorios respectivos. Incluye la imagen base y el hash del código corregido. `scripts/publicar-checkout-t08.py` publica estos tags una sola vez; `Dockerfile.t08` reutiliza la base original con sus dependencias fijadas, compila y ejecuta las pruebas sin instalar paquetes por red. La selección y los rollouts posteriores no construyen ni publican imágenes. Se conservan catorce artefactos en cinco repositorios.

Orders también tenía `product_id` configurado como índice de una `List` de Spring Data JDBC: dos UUID enviados se guardaban como `"0"`/`"1"`. Se cambió la colección a `Set`/`LinkedHashSet`, con `order_id` como vínculo al padre y sin `keyColumn`; no hay migración SQL. El DTO HTTP sigue exponiendo una lista mediante MapStruct y los eventos conservan sus ítems. Se recompilan todas las fuentes y los mappers con Java 21. Cuatro pruebas Java y la regresión local de PostgreSQL 17 verifican dos productos, cantidades y precios en SQL/API y tras reiniciar Orders, para ambos artefactos. La misma regresión falla con la imagen original.

`scripts/publicar-orders-t08.py` publica esta corrección con la base original fijada por digest y conserva las entradas de Checkout. Ambos publicadores rechazan tags existentes sin un registro de digest/hash de fuente coincidente; su repetición conserva las otras correcciones del manifest. No se reconstruye durante selección, plan o rollout. Los JAR publicados se contrastaron por SHA256 contra el JAR probado localmente.

## Operación

Desde la raíz del repo, con infra T06 creada, bootstrap listo y releases ECR existentes:

```bash
python3 scripts/estado.py init aplicacion --bucket the-store-tfstate-891200271122-us-east-1
terraform -chdir=terraform/aplicacion init
python3 scripts/aplicacion.py apply
python3 scripts/acceso.py run -- python3 scripts/probar-aplicacion.py --version v1
```

El operador abre/verifica ambos túneles, precarga la versión de tfvars, genera un plan privado, comprueba que solo opere objetos Kubernetes propios y aplica dentro de la misma sesión. Rechaza eliminaciones/reemplazos de app durante apply; T09 puede crear/retirar policies. No opera infra/ECR/IAM. `plan` comprueba lo mismo y cierra sin aplicar; su plan guardado queda protegido por el guard T04 y no se reutiliza después de cerrar los túneles. Para inspección manual, usar `acceso.py run -- ...` y conservar plan/apply en una misma sesión válida.

Para cambiar a v2, editar solo `app_version` en tfvars y repetir apply; no reconstruir ni sobrescribir tags. El arnés T12 verifica continuidad y rollback como campaña aparte.

Para retirar:

```bash
python3 scripts/aplicacion.py destroy
# Comprobar objetos eliminados en ambos kind mientras todavía hay acceso.
# Después revisar/applicar destroy de terraform/infra; conservar ECR/estado.
```

## Pruebas y límites

```bash
python3 -m unittest discover -s tests -q
terraform -chdir=terraform/aplicacion fmt -check -recursive
terraform -chdir=terraform/aplicacion validate
terraform -chdir=terraform/aplicacion test -filter=tests/aplicacion.tftest.hcl
```

La sonda real exige veinte pods Ready y referencias/digests runtime correctos, LabRole temporal desde Cart/Orders, NodePort/ClusterIP y versión UI por cada host y ALB. Escribe un carrito y checkout exclusivos desde A y los lee desde B, luego invierte los papeles. Usa APIs reales de Cart/DynamoDB, Checkout/Redis y Orders/PostgreSQL; correlaciona cada orden con su mensaje SQS nuevo para comprobar el SDK de Orders. Retira los carritos/keys de Checkout propios; las órdenes de demostración permanecen hasta destruir datos. No purga SQS y restaura visibilidad de mensajes recibidos. No equivale a la compra por navegador/Cypress, la persistencia ante reinicios ni la campaña T12: esas verificaciones siguen en T11/T12.

## Recuperación del entorno de laboratorio

Al iniciar T08, STS funcionaba pero el bucket y los cinco repositorios ECR ya no existían; es compatible con un reset externo del Learner Lab. El cierre T06/T07 había auditado su conservación. Se recuperó el bucket con comprobación de propiedad/etiquetas y se reaplicaron TLS/versionado/cifrado de bootstrap. Infra/app estaban vacías al cierre previo. Se recrearon los cinco repositorios inmutables y se restauraron las diez imágenes locales originales sin build, contrastando cada digest contra el manifest registrado. No se adoptan recursos ajenos ni se fuerza un manifest a coincidir.

Después de recuperar bootstrap e inicializar/aplicar la raíz imágenes, con las copias originales aún presentes en Docker local:

```bash
python3 scripts/publicar-imagenes.py restore v1
python3 scripts/publicar-imagenes.py restore v2
```

`restore` comprueba inmutabilidad, cuenta/repositorios, manifest y RepoDigests locales antes de hacer push. Omite tags remotos que ya coincidan y rechaza cualquier digest diferente. No construye, sobrescribe ni modifica el manifest. Si falta la copia local exacta, se detiene: no presenta una reconstrucción como recuperación del mismo artefacto.

Con la latencia observada se amplió la lectura inicial de outputs a 240 segundos y las consultas de identidad Kubernetes a 10 segundos por petición/30 por proceso. El guard conserva todas las comprobaciones de certificados, propietario de sesión, túneles y UID de ambos destinos. Los errores detallados quedan privados en `.local/acceso-error.log`; la salida external mantiene el mensaje genérico y nunca devuelve certificados.

Referencias: [mapeo de colecciones en Spring Data JDBC](https://docs.spring.io/spring-data/relational/reference/3.5/jdbc/mapping.html), [precarga e imagePullPolicy en kind](https://kind.sigs.k8s.io/docs/user/quick-start/), [referencias por digest en Kubernetes](https://kubernetes.io/docs/concepts/containers/images/), [IMDS y contenedores](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html).

## Cierre real T08 — 03/11/2026

La campaña AWS aprobó veinte pods Ready, los digests seleccionados en runtime, IMDSv2/LabRole desde Cart/Orders, UI directa de cada EC2 y ambos targets ALB healthy. Las dos compras API A→B y B→A conservaron producto, cantidad, precios y dirección en Orders/PostgreSQL, compartieron Cart/DynamoDB y Checkout/Redis y produjeron eventos SQS de las órdenes nuevas. El arnés restaura la visibilidad de los mensajes y acepta las respuestas vacías de las operaciones AWS que no devuelven payload.

Los tres planes reales finales (infra, imágenes y aplicación) convergieron sin cambios. La prueba negativa preparó un plan guardado de dos actualizaciones UI, cortó solo el túnel B y comprobó rechazo antes de modificar A: generaciones, réplicas y templates permanecieron idénticos. Los publicadores de Checkout y Orders se repitieron sin alterar el manifest ni los artefactos.

Pruebas de regresión: 75 Python, diez Terraform, dos Jest y cuatro Java. La infraestructura permanece disponible para T09; consultar `estado-tareas.md` para el cierre posterior y la auditoría de limpieza.
