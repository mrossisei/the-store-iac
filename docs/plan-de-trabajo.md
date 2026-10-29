# Plan para completar el TPE — Grupo 2

Relevamiento: **29/10/2026**. Entrega: **4/11/2026, 23:59**, según el enunciado. Exposiciones: 5 o 10/11, según el sorteo; máximo 30 minutos y participación de los tres.

> **Base del relevamiento: `89be2d7`.** Al publicar este documento se detectaron dos commits más nuevos en `origin/main`: `b0b5858` (ALB, subredes de datos y endpoints) y `3d70150` (NAT por zona, Multi-AZ y endpoint SQS). El diagnóstico y las validaciones de abajo corresponden al checkout anterior, no al nuevo HEAD remoto. Antes de repartir implementación, contrastar especialmente T03–T09 con esos cambios y convertir lo ya implementado en tareas de revisión y pruebas. No se volvieron a ejecutar las validaciones sobre esos dos commits durante la publicación.

## 1. Qué hay que entregar

La referencia de alcance es **`../../Pre Entrega - Grupo 2 .pdf`**, especialmente las secciones 2–4. El enunciado exige implementar el 100% de lo propuesto, una demostración funcional, presentación PPT, código en GitHub y un how-to. La preentrega del directorio `docs/`, el README y el guion de presentación describen una arquitectura anterior; no deben usarse para recortar el alcance del PDF final.

El trabajo elegido es **Infraestructura como Código con Terraform**. No hace falta desarrollar una tienda nueva: se reutilizan los cinco microservicios provistos y se termina su infraestructura en AWS.

El resultado comprometido es:

- VPC `10.0.0.0/16` en `us-east-1a` y `us-east-1b`.
- Públicas `10.0.1.0/24`, `10.0.2.0/24`; privadas para nodos/pods `10.0.16.0/20`, `10.0.32.0/20`; datos `10.0.48.0/24`, `10.0.49.0/24`.
- Internet Gateway, un NAT por AZ, rutas privadas hacia el NAT de su AZ y subredes de datos sin ruta por defecto a Internet.
- Endpoints Gateway de S3 y DynamoDB, e Interface de SQS con DNS privado.
- EKS, nodos AL2023 `t3.medium`, grupo administrado con capacidad entre 2 y 4 nodos, API privada para nodos y pública para operar desde las máquinas del grupo. Services `172.20.0.0/16`.
- **LabRole preexistente**, sin crear roles IAM para clúster/nodos/controlador, y AWS Load Balancer Controller que crea un **ALB público con targets IP** para la UI.
- Cinco repositorios ECR e imágenes `linux/amd64`, versión controlada por `app_version`.
- MySQL y PostgreSQL RDS en Multi-AZ; Redis con primaria y réplica en AZ distintas; DynamoDB y SQS. Bases en las subredes de datos, con puertos admitidos solo desde el SG de nodos.
- Dos réplicas **de cada uno de los cinco servicios**, distribuidas entre zonas. Flujo HTTP UI → Catalog/Cart/Checkout, Checkout → Orders; conexiones a datos en 3306, 5432, 6379 y HTTPS/443.
- NetworkPolicies con permisos específicos por servicio y cuarentena de Checkout que bloquee entrada y salida.
- Estado remoto S3 cifrado, privado, versionado y con bloqueo nativo.
- Cuatro demostraciones: creación/drift/destrucción; UI 2→4 y nodos 2→3→2; versión nueva y rollback sin corte; cuarentena y recuperación.

Fuera de alcance del PDF final: TLS, CI, observabilidad, autoescalado y roles IAM por microservicio. No agregarlos antes de completar y probar lo comprometido.

## 2. Qué está hecho y cuánto se puede confiar en ello

| Parte | Evidencia en el repositorio | Estado frente al PDF final |
|---|---|---|
| Aplicación original | `the-store/src/{ui,catalog,cart,orders,checkout}`; Dockerfiles y configuraciones de persistencia | Reutilizable. No se ejecutó la tienda en este relevamiento. |
| Estructura Terraform | Raíz y cinco módulos: red, cluster, imagenes, datos, aplicacion | Hecha y legible; conservar esta división. |
| Red | VPC, 2 públicas + 2 privadas, IGW, 1 NAT, rutas | Adaptar: CIDR públicas, 2 subredes de datos, segundo NAT, rutas y endpoints. |
| EKS | Módulo comunitario `~> 21.25`, managed node group, VPC CNI con NetworkPolicies | Adaptar a LabRole y revisar defaults que crean IAM/OIDC/KMS; verificar escalamiento. |
| Ingreso | Helm ingress-nginx, Service LoadBalancer/NLB, Ingress clase nginx | Sustituir por AWS LBC + ALB; actualizar la fuente del output `url`. |
| ECR/imágenes | Un repo y build/push Docker por servicio, plataforma amd64 | Base hecha; falta demostrar rollback que conserve el artefacto viejo. |
| Datos | Dos RDS `multi_az = false`, Redis de un nodo, DynamoDB con índice, SQS, SG | Adaptar a subredes de datos y Multi-AZ; quitar creación/adjunción de política IAM. |
| Deployments/Services | Variables de conexión, readiness probes, Services 80→8080, spread por zona | UI tiene 2 réplicas; los otros 4 tienen 1. El spread es preferente (`ScheduleAnyway`). |
| NetworkPolicies | Deny ingress, UI desde namespace nginx, permiso amplio frontend/backend, cuarentena por tier | Rehacer permiso de ALB y matriz entre servicios; conservar exclusión de cuarentena en todas las reglas allow. |
| Estado remoto | Bootstrap S3, versionado, acceso público bloqueado, `use_lockfile = true` | Falta nombre real de bucket: backend contiene `the-store-tfstate-CAMBIAR`. Verificar cifrado efectivo. |
| Verificación | `verificar.sh`, Cypress E2E original, generador Artillery | Hay material aprovechable; el script actual no prueba todos los compromisos y puede dar falsos positivos. |
| Documentación | README, decisiones, guía Terraform, guion oral y diagramas | Existe, pero requiere sincronización con ALB/LabRole/Multi-AZ/endpoints. No hay PPT final en los archivos relevados. |

### Comprobaciones realizadas ahora

- `terraform fmt -check -recursive terraform`: **pasa**.
- `terraform init -backend=false -lockfile=readonly -input=false` y `terraform validate` en la raíz: **pasan**. Se usó `TF_DATA_DIR` temporal, sin conectar el backend ni crear infraestructura. El rango del módulo EKS resolvió a **21.29.0**.
- Inicialización de `bootstrap` con el provider AWS ya descargado y `terraform validate`: **pasan**.
- `bash -n verificar.sh the-store/local.sh`: **pasa**.
- Terraform 1.16.1, AWS CLI y Docker están disponibles; el daemon Docker responde. **kubectl no está en PATH** de esta máquina.
- No se ejecutaron `plan`, `apply`, `destroy`, builds, Cypress ni pruebas contra AWS. Por tanto no hay evidencia nueva de funcionamiento integrado, permisos de Learner Lab, tiempos o costos reales.
- `docs/decisiones.md` registra una prueba anterior de kind 19/19 y AWS pendiente. Eso es una afirmación histórica del documento; la rama kind y ese resultado no se reprodujeron aquí.

La validación estática confirma que Terraform acepta la configuración actual, no que esta cumpla el PDF ni que AWS la vaya a permitir.

### Problemas que pueden hacer perder tiempo o falsear resultados

1. **LabRole no implica viabilidad automática.** Verificar sus permisos, confianza, PassRole, acceso desde pods y restricciones de servicios/instancias del laboratorio. El controlador necesita permisos de ELB/EC2 y credenciales dentro del pod; no alcanza con escribir un ARN en el ServiceAccount. Si el laboratorio impide un requisito, documentarlo y resolverlo con la cátedra antes de invertir días en esa parte.
2. **Credenciales de pods.** Los SDK de Cart/Orders usan la cadena de credenciales de AWS. En el módulo EKS descargado el hop limit de IMDSv2 predeterminado es 1. Si se hereda LabRole del nodo, configurar y probar la vía de credenciales para pods, incluidos Cart, Orders y LBC. El POC excluye roles separados por servicio.
3. **Escalamiento real.** El submódulo EKS ignora modificaciones posteriores de `desired_size`. Actualmente el código mueve min/desired/max juntos; eso tampoco representa un rango estable 2–4. Con límites 2 y 4, cambiar solo `desired_size` puede no escalar. Resolverlo en T04 y probar subida y bajada. Una opción es conservar el módulo para EKS y administrar el node group directamente en Terraform, para controlar su tamaño sin ese ignore; elegir una solución y mantener un solo dueño del recurso.
4. **Rollback del código.** El build actual depende del tag y usa el árbol de fuentes presente. Volver de `1.1` a `1.0` puede reconstruir código nuevo con el tag viejo. El criterio de éxito es volver al digest anterior y al contenido anterior, cambiando solo `app_version`.
5. **Falsos positivos de red.** `abierto()` considera abierto cualquier retorno distinto de timeout 28, incluidos DNS fallido, conexión rechazada o fallo de `kubectl exec`. Las pruebas negativas del pod intruso también pueden pasar si el pod o `nc` no funcionan. Verificar primero que la sonda arranca, tiene herramienta y resuelve el destino; distinguir error de ejecución de bloqueo esperado.
6. **Prueba de persistencia débil.** Buscar `createdDate` en cualquier orden no demuestra que la compra recién hecha quedó guardada. Correlacionar el ID de esa compra, verificarla y volver a leerla después de reiniciar pods. Probar también DynamoDB, Redis y el evento de SQS.
7. **Cuarentena por template.** Cambiar `tier` en el template genera un rollout; no es un cambio instantáneo sobre los pods actuales. Medir la convergencia y probar TODOS los pods de Checkout después de ella. Las NetworkPolicies son aditivas: ninguna regla allow debe seguir seleccionando pods en cuarentena por `app` solamente. Usar también IPs conocidas para comprobar que no se está viendo solo un fallo de DNS.
8. **Destrucción y recreación.** ALB y sus ENI son creados por el controlador, no directamente por el provider AWS. Borrar Ingress con el controlador operativo y verificar la liberación antes de eliminar red/clúster. Probar además el primer apply desde cero: Kubernetes/Helm se conectan a un EKS que se está creando en la misma raíz. No darlo por resuelto mediante un segundo apply manual sin documentar y corregir la causa.

## 3. Cómo dividirse sin pisarse

Se proponen tres responsables, a asignar entre Matías, Juan Pablo y Federico según afinidad:

| Frente | Responsable | Archivos propios | Primera entrega |
|---|---|---|---|
| **A — Red, datos y estado** | Una persona | `modules/red`, `modules/datos`, `bootstrap`, `backend.tf` | Contrato de subredes y conexiones, luego red y bases finales. |
| **B — EKS, ALB y coordinación Terraform** | Una persona | `modules/cluster`, raíz `main.tf`, `providers.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars`, locks; coordinación de `verificar.sh` | Factibilidad Learner Lab, clúster con LabRole y controlador. |
| **C — Aplicación y versiones** | Una persona | `modules/imagenes`, `modules/aplicacion`, helpers de build/rollback y E2E | Artefactos versionados, 10 réplicas base y políticas finales. |

Cada responsable prepara y ejecuta las pruebas de su parte. En T10, B arma el arnés común, A aporta las pruebas de red/datos y C las funcionales. En T11–T13 trabajan juntos; C coordina la integración, B los planes de cambios y A la limpieza. Revisiones cruzadas: A revisa B; B revisa C; C revisa A.

**Dos conceptos distintos:** pueden escribir los módulos en paralelo apenas acuerden sus interfaces en T00. Las dependencias del mapa indican cuándo una tarea puede verificarse y cerrarse sobre AWS; no obligan a esperar para empezar a programarla.

Usar una rama por frente y cambios chicos. B integra las conexiones en la raíz, para evitar que los tres editen `main.tf`, variables y tfvars al mismo tiempo. **Un solo operador ejecuta planes/apply/destroy sobre el entorno compartido en cada sesión**; el bloqueo S3 protege el estado, pero no coordina cambios de código diferentes. Los demás revisan y registran evidencia. No hacer apply desde tres ramas distintas contra el mismo estado.

## 4. Tareas, dependencias y aceptación

Las horas son de trabajo activo estimado por tarea, no incluyen esperas de AWS y no son una garantía. Se ajustan después de T01. `Depende de` significa dependencia para **cerrar la tarea en el entorno integrado**.

### T00 — Fijar alcance e interfaces · Todos · 0,5–1 h · Sin dependencias

**Hacer:** registrar el PDF final como contrato; acordar nombres y tipos de variables/outputs. Convenciones propuestas: `data_subnets`, `data_subnet_ids`, `private_route_table_ids`, `nat_public_ips` (lista), `lab_role_arn`, `node_security_group_id`, `public_subnet_cidrs`. Conservar las claves de `databases` e `images` para reducir cambios. Definir de antemano cómo devolver el hostname del ALB desde el Ingress de aplicación, sin ciclo cluster→aplicación→cluster.

**Aceptación:** los tres pueden implementar contra las mismas firmas; hay un dueño de archivos compartidos y la matriz de requisitos del apartado 2 está aceptada como backlog. No modificar silenciosamente el alcance entregado.

### T01 — Verificar Learner Lab y herramientas · B · 1–2 h · T00

**Hacer:** comprobar sesión AWS vigente, región/AZ, LabRole y permisos efectivos para EKS/nodos/LBC, DynamoDB/SQS, endpoints, NAT/EIP, RDS Multi-AZ y Redis con réplica; revisar cuotas y servicios/tipos habilitados, roles vinculados a servicios y capacidad de pasar el rol. Instalar/verificar kubectl en la máquina operadora. Revisar versiones de EKS, add-ons, chart y motores disponibles y fijar una combinación. Estimar el costo de la arquitectura final con presupuesto del Lab; el costo viejo del README no aplica automáticamente.

**Aceptación:** lista escrita de permitido/no permitido y acceso comprobado. Si falta un permiso, existe una resolución concreta con la cátedra; no se sustituye ALB o Multi-AZ por otra cosa sin acuerdo. Las credenciales se configuran fuera de Git; las temporales incluyen su token de sesión.

### T02 — Preparar estado compartido y base reproducible · A, B integra locks · 1–2 h · T01

**Hacer:** crear/configurar bucket real, validar cifrado, versionado y acceso privado; configurar backend y bloqueo nativo. Registrar versiones elegidas y fijar la versión exacta del módulo EKS ensayado (el lock fija providers, no versiones de módulos). Mantener inventario del bootstrap y conservar su estado local en lugar seguro.

**Aceptación:** inicialización remota correcta; escritura/lectura de estado y bloqueo comprobados en una prueba controlada; dos operadores ven el mismo entorno. Se documenta que el bucket y sus versiones de estado se conservan intencionalmente después del destroy de la aplicación, al igual que LabRole preexistente.

### T03 — Completar la red del PDF · A · 3–5 h · T02

**Hacer:** corregir CIDR públicas; crear subredes de datos y sus asociaciones explícitas a tablas sin ruta por defecto; dos NAT/EIP y rutas privadas por AZ. Endpoints S3/DynamoDB Gateway con tablas pertinentes, y SQS Interface en privadas, DNS privado y SG TCP/443 desde nodos. Acordar con B el enlace del SG del endpoint para evitar una dependencia circular red↔cluster. Exportar IDs/CIDR/rutas requeridos.

**Aceptación:** inventario AWS muestra seis subredes sin solapamiento; rutas privadas salen por su propio NAT y las de datos solo tienen ruta local; endpoints `available`. Un origen de prueba con los permisos correspondientes resuelve SQS a IP privada y accede a S3/DynamoDB por sus rutas de endpoint. El SG del endpoint no admite 443 desde Internet.

### T04 — EKS con LabRole, dos zonas y escalamiento · B · 3–5 h · T03

**Hacer:** usar LabRole existente en control plane y node group, deshabilitar creación de roles/políticas y recursos auxiliares no permitidos por el Lab; no basta con deshabilitar un único rol. API privada y pública según PDF, AL2023, nodos privados y VPC CNI con soporte de NetworkPolicies. Resolver acceso IAM desde pods. Implementar el tamaño deseado sin que `ignore_changes` anule el caso de uso; rango 2–4.

**Aceptación:** dos nodos Ready, evidencia de ambos AZ y de ausencia de IP pública; operadores acceden a la API, pods de prueba obtienen identidad y permisos previstos. Configuración permite subir 2→3 y bajar 3→2 con Terraform, sin reemplazar el clúster. La prueba completa de escala con UI se cierra en T12.

### T05 — AWS Load Balancer Controller · B · 2–4 h · T04

**Hacer:** sustituir chart nginx por AWS LBC; usar la vía de credenciales LabRole comprobada, configurar región/VPC y acceso al webhook. Preparar SG de ALB/nodos para targets IP y HTTP/8080. Quitar outputs que leen el Service nginx y acordar su reemplazo en T08.

**Aceptación:** controlador disponible, webhook accesible y sin errores de permisos; no se crean nuevos roles IAM. La prueba del ALB público, health checks y URL real se cierra con el Ingress en T11. No debe quedar un NLB/nginx viejo ocultando fallas del ALB.

### T06 — Datos en Multi-AZ e integración con LabRole · A · 3–5 h · T03, T04

**Hacer:** pasar RDS/Redis a `data_subnet_ids`; habilitar Multi-AZ en ambas RDS y primaria/réplica Redis con failover y distribución entre AZ (replication group en lugar del cluster de un nodo). Exponer endpoint de escritura estable; acordar endpoint de lectura de Redis con C si se usa. Conservar tabla DynamoDB/índice y SQS. Eliminar la política IAM y el attachment que crea hoy el módulo; verificar permisos reales de LabRole.

**Aceptación:** AWS confirma Multi-AZ de las dos RDS y dos nodos Redis en AZ distintas; bases sin acceso público y puertos limitados al SG de nodos. Se prueban conexión y escritura/lectura válidas, y rechazo desde un origen no autorizado que tenga conectividad al destino. Se mantienen los nombres/claves que usa la aplicación. No se exigen cambios al esquema de las aplicaciones para completar esta tarea.

### T07 — Versiones y rollback de artefactos · C · 2–4 h · T02

**Hacer:** conservar build/push de los cinco servicios en amd64, pero hacer que `app_version` resuelva a un artefacto estable. Propuesta: al publicar un tag inexistente construirlo y guardarlo; si el tag ya existe reutilizarlo sin reconstruirlo ni sobrescribirlo, con tags inmutables y un helper invocado desde Terraform si es necesario. Diferenciar tag inexistente de error de permisos. Preparar contenido visible v1/v2 y registrar sus digests.

**Aceptación:** el primer tag se construye/publica, cambiar a otro crea la versión nueva y volver al primero despliega el **mismo digest anterior**, aunque el árbol de fuentes siga en v2. No requiere editar otra variable ni restaurar código para el rollback. Un apply posterior sin cambios no reconstruye ni altera recursos.

### T08 — Aplicación final e Ingress ALB · C, B conecta raíz · 2–3 h · T04, T05, T06, T07

**Hacer:** dos réplicas por servicio, colocación entre AZ con una condición que garantice la distribución requerida y diagnóstico de pods Pending; readiness/rolling update y capacidad para el pod adicional durante despliegues. Ingress clase ALB, público, targets IP, HTTP/80, health check de UI compatible. URL desde el status de ese Ingress con espera explícita hasta tener hostname; nunca devolver una URL `pendiente` como éxito. Revisar todas las variables de persistencia, sin fallback accidental a memoria.

**Aceptación:** configuración válida y diez pods de aplicación Ready, dos por servicio y uno de cada servicio por AZ en baseline; referencias de imágenes correctas. Documentar requests/espacio para rollouts en dos t3.medium. Checkout usa Redis y los servicios AWS reales. La conectividad pública con todas las políticas se acepta en T11.

### T09 — Matriz de red y cuarentena · C, B revisa · 2–4 h · T08

**Hacer:** reemplazar permiso desde namespace nginx por ingreso desde CIDR públicas del ALB a UI:8080, coordinado con sus SG y health checks. Permitir UI→Catalog/Cart/Checkout y Checkout→Orders; cualquier excepción se justifica leyendo un consumidor real. Evitar la regla genérica todos-los-backends→todos-los-backends. Preservar cuarentena de entrada y salida excluyendo `tier=cuarentena` en cada regla allow.

**Aceptación:** matriz positiva y negativa probada (incluye Catalog→Orders rechazado y pod sin etiquetas→UI/backend rechazado). ALB sirve UI y pasa health checks. En cuarentena, todos los pods Checkout pierden acceso a servicios, Redis, DNS e Internet, y no reciben de UI; catálogo/carrito siguen operativos. Vaciar lista restaura compra. Registrar convergencia del rollout y enforcement del CNI; no suponer aislamiento desde el primer milisegundo.

### T10 — Verificaciones fiables y evidencia · B coordina; A/C aportan · 2–4 h por responsable · T00

**Hacer:** corregir `verificar.sh`: precondiciones, jq para outputs JSON, timeouts/reintentos con límite, clasificación de fallos y limpieza de sondas/cookies mediante trap. Usar herramientas de sondeo comprobadas o imagen de diagnóstico; no asumir curl/nc dentro de cada app. Comprobar diez réplicas Ready y AZ, conectividad real, compra identificable, persistencia tras reinicio, endpoints/SG/Multi-AZ y SQS. Reutilizar Cypress para flujo de navegador. Artillery queda como herramienta disponible para actividad de prueba, no como un sistema nuevo a desarrollar.

**Aceptación:** script falla con salida distinta de cero si falta kubectl, el pod de prueba no arranca, falta curl/nc o un destino que debería responder no lo hace. Pruebas negativas solo pasan con precondiciones válidas y bloqueo esperado. Cada resultado incluye fecha, commit, prueba y evidencia sin secretos. Esta tarea se puede preparar en paralelo; su ejecución real se cierra en T11.

### T11 — Integrar y probar el entorno completo · Todos, C coordina · 3–5 h de sesión · T01–T10

**Hacer:** integrar ramas; fmt/validate, plan revisado y primer apply final. Ejecutar arnés, Cypress y matriz de infraestructura/red; registrar tiempos reales. Después ejecutar otro plan para comprobar convergencia.

**Aceptación:** tienda pública detrás de ALB, compra completa identificada, datos conservados al recrear pods, evento nuevo en SQS; arquitectura del PDF comprobada. `terraform plan -detailed-exitcode` devuelve **0** después de estabilizar, no 2 ni 1. La prueba de bloqueo y la inspección de rutas/SG no se sustituyen por un HTTP 200.

### T12 — Ensayar los cuatro casos de uso · Todos · 4–6 h de sesión · T11

**Hacer:** ejecutar los casos con plan antes de apply, guardar evidencia y restaurar baseline entre ellos. Para drift, alterar manualmente un recurso administrado, preferentemente desde consola como propone el PDF; documentar el campo y corrección. Para escala, cambiar solo UI 2→4 y nodos 2→3; para versiones, solo `app_version`; para cuarentena, solo `quarantine`.

**Aceptación:** matriz del apartado 6 completa. Escala produce dos recursos modificados (Deployment UI y node group); cuarentena un Deployment. Diferenciar cantidad de atributos de cantidad de recursos. Rollback recupera digest y contenido; sondeo continuo y actividad funcional no muestran cortes durante actualización/rollback. Quarantine no afecta catálogo/carrito y su reversión recupera checkout. Cada caso vuelve a plan sin cambios.

### T13 — Destruir, auditar huérfanos y recrear · Todos, A coordina · 2–4 h de sesión · T12

**Hacer:** destroy del entorno de prueba con el controlador vivo hasta liberar ALB; revisar inventario por IDs/tags y dependencias (incluye ENI, SG, endpoints, NAT, EIP, repositorios y datos). Recrear desde cero con el mismo código y artefactos/fuentes documentados; repetir smoke/E2E. Destruir al cerrar la sesión salvo uso acordado para ensayo inmediato.

**Aceptación:** sin recursos facturables del entorno remanentes; excepciones explícitas: bucket/estado del bootstrap y recursos preexistentes del Lab. No buscar solo por tags, porque los recursos del controlador pueden usar tags distintos. Recreación y posterior limpieza funcionan y están registradas. El destroy borra los datos de prueba por diseño; persistencia se exige ante reinicio de pods, no ante destroy de las bases.

### T14 — How-to, informe final, PPT y ensayo oral · Todos · 2–3 h por persona + ensayo · T13

**Hacer:** A documenta red/datos/bootstrap y limpieza; B arquitectura EKS/ALB/LabRole, versiones y comandos; C casos de uso, imágenes y evidencia. Actualizar README, decisiones, guía y presentación para que no contradigan al PDF final. Preparar documento final explicativo, PPT real, grabaciones de respaldo y link GitHub accesible para la cátedra. El borrador puede iniciarse desde T00; se cierra con resultados de pruebas reales.

**Aceptación:** otra persona sigue el how-to sin completar pasos ocultos; los tres hablan y pueden responder por el conjunto; ensayo menor a 30 min (propuesta: 12 explicación + 15 demo + 3 margen). Entregables subidos al Campus antes del 4/11 a las 23:59. No prometer tiempos de apply/destroy que no se midieron. El PDF de preentrega tiene 5 páginas contando portada y 4 de contenido; si la cátedra solicita ajuste al límite de 4, confirmar cómo cuenta la portada.

## 5. Mapa de dependencias

Versión visual interactiva: **`mapa-de-tareas.html`**, abrir en navegador. La siguiente lista es la misma información en texto, sin depender del visor:

```text
T00 → T01 Factibilidad Lab → T02 Estado → T03 Red → T04 EKS → T05 ALB
T02 → T07 Imágenes (en paralelo al camino de red/clúster)
T03 + T04 → T06 Datos
T04 + T05 + T06 + T07 → T08 Aplicación → T09 Políticas
T00 → T10 Preparar verificaciones (en paralelo)

T01 a T10 completos → T11 Integración
                    → T12 Cuatro casos de uso
                    → T13 Destroy + recreación + limpieza
                    → T14 Entrega y ensayo final
```

Ruta que merece mayor atención: **Lab → red → EKS → ALB/datos → aplicación → políticas → integración**. Es una ruta probable por dependencias, no un cálculo de CPM con duraciones medidas. Imágenes o permisos pueden convertirse en el cuello de botella; empezar T01 y T07 el primer día. Preparar T10 y documentación desde el inicio.

## 6. Plan de pruebas y evidencia mínima

| Prueba | Estímulo y evidencia que debe quedar | Responsable principal |
|---|---|---|
| Estática | fmt, validate raíz/bootstrap, versiones/locks y revisión del plan | B; cada frente antes de integrar |
| Red | Inventario de 6 CIDR, asociaciones de rutas, NAT por AZ, endpoints/DNS privado y SG | A |
| Alta disponibilidad declarada | RDS Multi-AZ; Redis primaria/réplica en AZ distintas; nodos y pods por zona | A + B + C |
| Flujo E2E | Home/catalog/cart/checkout, orden nueva con ID, registro PostgreSQL y evento SQS correlacionado | C + A |
| Persistencia de aplicación | Guardar carrito/checkout/orden, reiniciar los pods pertinentes y recuperar los mismos datos | C + A |
| Segmentación | Permisos y rechazos de T09; precondiciones válidas de cada sonda | C + B |
| Caso 1 | Crear; cambiar recurso fuera de Terraform; plan detecta drift; apply lo corrige; plan=0. Destroy y recreación en T13 | B + A |
| Caso 2 | Solo UI 2→4 y nodos 2→3, plan de dos recursos, 12 pods app Ready y 3 nodos; volver a 10 pods/2 nodos | B + C |
| Caso 3 | Digest y contenido v1→v2→v1; fechas/status HTTP y compras durante ambos rollouts; sin errores observados | C |
| Caso 4 | Solo quarantine cambia un Deployment; cortar entrada/salida en todos los pods Checkout, mantener catálogo/carrito y luego recuperar compra | C + B |
| Convergencia | Después de cada caso, `terraform plan -detailed-exitcode`: 0; error=1, cambios=2 | B |
| Ciclo completo | Destroy, inventario sin huérfanos, recreate y smoke/E2E, limpieza final con excepciones identificadas | A + todos |

Para SQS no basta con comprobar que la cola existe: registrar el evento de la compra, considerando su posible demora y evitando atribuir un mensaje viejo a la prueba. Para Multi-AZ se exige evidencia de configuración/topología; un ensayo real de failover es una prueba adicional útil si el Lab y el tiempo lo permiten, no un quinto caso de uso prometido.

Guardar evidencia en un directorio por sesión/commit con una tabla de resultados, salidas relevantes y capturas/video. No subir tfstate, planes binarios, credenciales ni contraseñas. Las capturas de respaldo complementan la demo funcional; no reemplazan completar la implementación.

## 7. Calendario propuesto

| Fecha | Resultado esperado |
|---|---|
| **Jue 29/10** | T00 + T01, backend T02; abrir los tres frentes. B resuelve primero la viabilidad de LabRole/LBC, C comienza T07. |
| **Vie 30/10** | Red, EKS y datos avanzados en paralelo; imágenes y aplicación listas para conectar; T10 preparado. Primeras pruebas AWS por parte. |
| **Sáb 31/10** | Integrar T03–T09; objetivo: primer entorno final funcional. Resolver fallas de integración, no dejar permisos para el último día. |
| **Dom 1/11** | Cerrar T11 y empezar T12; registrar pruebas de los cuatro casos. |
| **Lun 2/11** | Completar T12 y ciclo destroy/recreate T13, actualizar tiempos y evidencia. |
| **Mar 3/11** | Cerrar T14: how-to, informe, PPT y ensayo completo. |
| **Mié 4/11** | Margen para fallas, revisión de enlaces/entregables y subida al Campus antes de 23:59. |

Si un requisito del Lab bloquea el alcance, tratarlo el 29/10; no gastar el margen del 4/11 descubriendo que la cuenta no permite crearlo. No iniciar extras mientras falte una fila de aceptación del PDF.

## 8. Referencias técnicas contrastadas

- [Instalación de AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/deploy/installation/): permisos del controlador, credenciales del nodo e IMDSv2.
- [Módulo EKS managed node group v21.25.0](https://github.com/terraform-aws-modules/terraform-aws-eks/blob/v21.25.0/modules/eks-managed-node-group/main.tf): `ignore_changes` de desired size; se verificó el mismo comportamiento en el 21.29.0 descargado durante el relevamiento.
- [NetworkPolicies en VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html): habilitación y enforcement al iniciar pods; revisar compatibilidad de la versión elegida.
- [Datos sensibles en Terraform](https://developer.hashicorp.com/terraform/language/manage-sensitive-data): `sensitive` oculta valores en pantalla, pero no los elimina del estado.

Se respetaron las modificaciones locales preexistentes en preentrega/diagramas. Este relevamiento agrega planificación; no adapta todavía la infraestructura ni certifica una ejecución AWS.
