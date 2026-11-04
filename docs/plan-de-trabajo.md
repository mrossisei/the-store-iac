# Plan para completar el TPE — versión vigente con EC2 + kind

**Plan base del 29/10/2026; ampliación operativa del 4/11/2026.** Reemplaza íntegramente el plan anterior basado en EKS. Entrega: **4/11/2026, 23:59**. Exposición: 5 o 10/11 según sorteo, máximo 30 minutos; deben hablar los tres.

**Estado vigente:** T00–T09 completas, T10 preparada; ver [estado de ejecución](estado-tareas.md). Se incorpora **T15 — GitHub Actions** por pedido del usuario, antes del cierre de T11, sin renumerar tareas. Los diagnósticos y el calendario del plan base se conservan como antecedentes; no describen el avance actual. Es una ampliación para operar el POC, no una nueva exigencia de la preentrega.

## 1. Fuentes y alcance correcto

- **Preentrega vigente:** [preentrega-vigente.pdf](preentrega-vigente.pdf), copia de `Pre Entrega - Grupo 2 -1.pdf` adjuntada por el usuario. SHA-256: `80182ed242aee54adf9777ff069a80d7011450ef3780dce07e55d97c9d8a988c`.
- **Consigna:** `Enunciado TPE 2026 2C-3.pdf`, en el directorio superior del proyecto. Exige cumplir lo propuesto, demostrarlo, entregar PPT y publicar código + how-to en GitHub.
- **Código revisado:** `origin/main` en **88e178a**, que incluye los cambios de infraestructura de `b0b5858` y `3d70150`. El checkout de trabajo original sigue en `89be2d7` y tiene cambios locales ajenos a este plan; el diagnóstico de abajo usa el remoto actualizado.
- `docs/preentrega.pdf`, sus fuentes MD/TEX y el README aún describen versiones anteriores. Para repartir este trabajo usar el PDF **vigente** enlazado arriba. No regenerarlo desde esas fuentes antiguas.

**El POC ahora usa dos EC2 privadas, una por AZ, y un clúster kind independiente en cada EC2.** No es un único clúster Kubernetes distribuido entre máquinas. Cada kind aloja una copia completa de los cinco microservicios, con dos réplicas de cada uno. Los servicios de datos administrados son compartidos por ambas copias.

| Antes, en la propuesta EKS | Ahora, según el PDF vigente |
|---|---|
| EKS y node group administrado | Docker + kind automatizados en dos EC2 Linux |
| ALB creado por AWS Load Balancer Controller a partir de un Ingress | ALB creado directamente con Terraform; targets EC2:8080 |
| ALB directo a IP de pod | ALB → EC2:8080 → mapeo kind → NodePort UI → pod |
| Pods con IP de las subredes AWS /20 | Privadas /24; pods en `10.244.0.0/16`, Services en `172.20.0.0/16` dentro de cada kind |
| Réplicas repartidas entre AZ en un clúster | Dos réplicas por servicio **en cada kind**, dentro de su EC2 |
| Escalar UI y cantidad de nodos | Escalar solo UI 2→4; no aumenta la capacidad física de la EC2 |
| Cambiar versión y reconstruir imágenes | Seleccionar imágenes inmutables **ya publicadas**; rollback sin rebuild |
| Cuarentena cambiando el template de pods | Cambiar **NetworkPolicies**, eliminando permisos de entrada/salida |
| Roles creados para EKS/LBC | Reutilizar **LabInstanceProfile + LabRole**, sin crear roles |

**Se mantiene:** VPC de dos AZ, seis subredes, dos NAT, endpoints, ALB, ECR, MySQL/PostgreSQL Multi-AZ, Redis primaria/réplica, DynamoDB, SQS y estado S3 cifrado/versionado/con bloqueo. Se simplifica el cómputo; estos componentes siguen comprometidos.

Direccionamiento del PDF:

| Uso | AZ a | AZ b |
|---|---|---|
| Públicas: ALB + NAT | `10.0.1.0/24` | `10.0.2.0/24` |
| Privadas: EC2 + endpoint SQS | `10.0.16.0/24` | `10.0.32.0/24` |
| Datos: RDS + Redis | `10.0.48.0/24` | `10.0.49.0/24` |

VPC: `10.0.0.0/16`. Cada kind usa pods `10.244.0.0/16` y Services `172.20.0.0/16`. No se enrutan esos CIDR de pods/Services entre los dos clústeres. Revisar también que la red bridge de Docker no se superponga con las otras.

Fuera de alcance: EKS como solución principal, TLS, observabilidad, autoescalado y nuevos roles por microservicio. GitHub Actions se incorpora como excepción explícita por pedido del usuario en T15: tres workflows manuales para plan/apply/destroy del POC existente, sin ampliar la arquitectura AWS.

## 2. Qué ya está hecho en el remoto y qué falta

| Parte | Estado real en 88e178a | Acción necesaria |
|---|---|---|
| Red | VPC, seis subredes, NAT por AZ, tablas, endpoints Gateway S3/DynamoDB e Interface SQS | **Reutilizar.** Cambiar privadas /20→/24, revisar SG/rutas y compatibilidad con EC2/kind. |
| ALB | Se solicita con un Ingress y AWS LBC instalado por Helm | **Reemplazar mecanismo.** Declarar ALB, listener, target group tipo instance y attachments en Terraform. |
| Cómputo | Módulo EKS + node group; crea roles y un rol IRSA de LBC | **Reemplazar por EC2 + LabInstanceProfile** y bootstrap Docker/kind/CNI. |
| Datos | Dos RDS con Multi-AZ; Redis replication group de dos nodos con failover; DynamoDB/SQS | **Reutilizar y adaptar al Lab.** RDS aún usa gp3, no el gp2 indicado por el PDF; cambiar SG de nodos EKS por SG de EC2. Quitar creación de política IAM y attachment. |
| Imágenes | ECR por servicio, build/push amd64 desde Terraform, tags MUTABLE y build ligado a app_version | **Separar publicación y selección.** Tags inmutables/digests, versiones preparadas y carga en ambos kind. |
| Aplicación | Cinco Deployments con dos réplicas y ClusterIP; Ingress ALB; spread entre AZ | **Reutilizar configuración de servicios.** Instanciar módulo dos veces, UI NodePort, quitar Ingress y supuestos de spread entre AZ. El código contiene dos bloques de spread equivalentes que deben revisarse al adaptar. |
| Policies | Deny ingress, UI desde CIDR del ALB, permiso amplio frontend/backend y cuarentena por tier del pod | **Adaptar a kind/CNI y al nuevo caso 4.** Reglas específicas, cuarentena por modificación de policies sin recrear los pods. |
| Estado | Bootstrap S3, versionado/bloqueo; backend con nombre CAMBIAR | Completar backend real y separar estados/configuraciones para permitir borrar aplicación antes que infraestructura. |
| Scripts de apoyo | `local.sh` sabe crear kind y cargar imágenes, pero instala nginx, pregunta interactivamente y aplica YAML con kubectl | Usarlo como referencia. Bootstrap no interactivo; Terraform conserva la propiedad de los objetos de aplicación. |
| Pruebas | `verificar.sh` orientado a EKS; Cypress original disponible | Adaptar a dos contextos kind, targets del ALB y pruebas de red fiables. |
| Documentación | README y guion explican EKS | Reescribir para el alcance vigente; conservar el PDF recibido como referencia. |

**Validado nuevamente sobre 88e178a:** `terraform fmt -check -recursive terraform`, `terraform validate` raíz y bootstrap, y `bash -n verificar.sh the-store/local.sh`: pasan. Inicialización sin backend con `TF_DATA_DIR` temporal y lock de providers en modo lectura. Módulos descargados: EKS 21.29.0 e IAM 6.8.2.

Estas verificaciones corresponden al código **actual de EKS**, no prueban la futura implementación kind. No se ejecutaron plan/apply/destroy, builds, Cypress ni pruebas AWS en esta revisión. No se certifican permisos, costos, tiempos o integración. La validación estática tampoco demuestra cumplimiento de la nueva preentrega.

## 3. Cómo lo implementaría

Mantener los cinco módulos, sustituyendo `cluster` por **`computo`**. La red y los datos existentes se adaptan; las configuraciones de los microservicios se reutilizan.

1. **Preparación y estados.** Propuesta: tres configuraciones Terraform con claves S3 distintas: infraestructura AWS, publicación de imágenes y aplicación Kubernetes. La de aplicación administra los **dos** kind mediante dos providers con alias y dos instancias del mismo módulo. Bootstrap del bucket separado. El `terraform.tfvars` de aplicación controla `replicas`, `app_version` y `quarantine` de ambos clústeres.
2. **EC2.** Una Linux x86_64 permitida por el Lab en cada privada, sin IP pública; perfil existente. User-data/scripts instalan Docker, kind, kubectl, AWS CLI y un CNI compatible con NetworkPolicies. Propuesta inicial: **Calico con CNI por defecto deshabilitado**, versiones fijadas y CIDR `10.244.0.0/16` configurado también en Calico. Un control plane y un worker dentro de cada host es una topología inicial suficiente; su cantidad no suma recursos físicos.
3. **Acceso administrativo.** Propuesta: SSM Session Manager sobre el perfil existente, con túneles autenticados a la API de cada kind. API en `127.0.0.1:6443` de la EC2; túneles locales diferenciados, por ejemplo 16443 y 26443. Kubeconfigs/CA y certificados propios por clúster; TLS validado. T01 debe comprobar que el Lab permite SSM, que el agente está online y que el usuario tiene permisos. No se da por hecho ni se requiere un bastion de entrada.
4. **Entrada web.** ALB público de Terraform con listener HTTP/80 y dos targets instance en 8080. Ejemplo acordable: EC2 hostPort 8080 → containerPort kind **30080**; el Service UI usa exactamente ese **nodePort 30080**, puerto 80 y targetPort 8080. El SG EC2 admite 8080 solo desde el SG ALB. Health check de UI `/actuator/health/readiness`.
5. **Imágenes.** Publicar v1/v2 desde el equipo del grupo con sus credenciales y conservarlas inmutables. Para kind, propuesta práctica: EC2 se autentica a ECR con LabRole, descarga la referencia seleccionada y usa `kind load` para cargarla en los nodos. Integrar esa preparación como dependencia automatizada del despliegue, verificando la referencia/digest real en containerd; no alcanza con descargarla al Docker del host. En los Deployments usar una política compatible con precarga, por ejemplo IfNotPresent. Cambio de `app_version` prepara y despliega artefactos existentes; no construye nada.
6. **Credenciales y datos.** Cart/Orders deben obtener credenciales temporales de LabRole desde sus pods y acceder a DynamoDB/SQS por los endpoints. Esa vía es distinta de autenticar el Docker del host para ECR: probar ambas. Comprobar IMDSv2 y sus saltos con las capas EC2→contenedor kind→pod; no trasladar automáticamente el hop limit de EKS. No copiar las claves personales del grupo dentro de los contenedores.
7. **Cuarentena.** Mantener un deny por defecto y permisos explícitos UI→Catalog/Cart/Checkout y Checkout→Orders. `quarantine` modifica las reglas de entrada/salida de Checkout en ambos kind; no necesita cambiar su PodTemplate ni reiniciar el proceso. Ninguna otra regla allow debe dejar abierto el camino. Las policies son aditivas: una policy llamada deny no revoca por sí sola permisos de otras.
8. **Operación.** Preparar acceso a APIs, aplicar app en ambos contextos, probar cada copia y luego el ALB. Para eliminar: destroy de aplicación en ambos kind mientras las EC2 siguen vivas; después infraestructura AWS y, cuando corresponda, repositorios de imágenes. Conservar intencionalmente bucket/estado y recursos IAM preexistentes.

Son decisiones de implementación propuestas, no hechos del PDF: **SSM, Calico, número de nodos internos, puertos concretos y distribución en estados** se cierran en T00/T01 con una prueba breve. Respetan el alcance sin agregar EKS, nuevos roles o un Ingress Controller.

### Riesgos que conviene resolver primero

- **RAM real:** con los requests del módulo actual, dos réplicas de los cinco servicios suman **4096 MiB por EC2**, antes de Linux, Docker, control plane/worker y Calico. UI 2→4 agrega 1024 MiB por host. Dos t3.medium no deben heredarse como elección automática: probar un tipo permitido con memoria suficiente y margen para rollouts, o ajustar requests con medición. Los nodos kind comparten la RAM del host.
- **Conteos:** baseline **10 pods app por kind, 20 total**; campaña **12 por kind, 24 total**. Esta es la interpretación operativa adoptada para aplicar la misma variable a ambos clústeres. No contar CNI, CoreDNS o control plane como pods de aplicación.
- **Sondeos a ambas copias:** el ALB puede devolver respuestas sanas de una EC2 y ocultar una copia rota. Probar contextos/targets A y B por separado y comprobar que ambos targets estén healthy.
- **Red dentro de Docker:** observar la IP de origen al atravesar NodePort y los SNAT de Calico/Docker al salir a RDS/endpoints. No copiar sin probar la policy de ALB→IP de pod de EKS. La frontera ALB→EC2 se protege con SG.
- **Caché y credenciales:** una imagen ya cacheada puede ocultar un problema de ECR. Probar una versión no cargada antes y en ambos clústeres. Verificar también renovación de credenciales temporales de Cart/Orders.
- **Primer apply y destroy:** providers Kubernetes no deben depender de un clúster inaccesible que se crea o destruye a la vez. Separar configuraciones permite ordenar los ciclos. Un túnel caído debe abortar antes de destruir EC2.
- **Estado AWS existente:** antes de quitar EKS o renombrar módulos, inventariar si hay recursos reales administrados. Revisar migración/recreación y el plan de destrucción; este documento no autoriza ni ejecuta esa migración.
- **Réplicas no equivalen a HA del clúster:** dentro de cada kind, perder su EC2 pierde todos sus pods. El ALB puede enviar a la otra copia sana; no es un clúster compartido que reprograme pods entre AZ.

## 4. Reparto en tres frentes

| Frente | Propiedad de archivos | Trabajo principal |
|---|---|---|
| **A — Red, ALB y datos** | `modules/red`, `modules/datos`, bootstrap/backend | T02, T05, T06: adaptar red existente, ALB con Terraform, compatibilidad de datos con Lab. |
| **B — EC2, kind y administración** | `modules/computo`, scripts de bootstrap/acceso, raíz/providers/variables/outputs/locks | T01, T03, T04: perfil existente, hosts, CNI, acceso a los dos Kubernetes y ciclo de estados. Coordina T10. |
| **C — Imágenes y aplicación** | `modules/imagenes`, `modules/aplicacion`, scripts de carga y Cypress | T07, T08, T09: publicación inmutable, dos despliegues, NodePort, políticas y pruebas funcionales. |

**T15:** B coordina `.github/workflows/`, el orquestador y las herramientas del runner; A revisa backend, planes y destroy; C revisa selección ECR, precarga y despliegue. La documentación de T14 avanza en paralelo.

Asignar A/B/C entre Matías, Juan Pablo y Federico según afinidad. Cada uno escribe las pruebas de su parte; B unifica el arnés. Los tres hacen integración, demos, limpieza y exposición. Revisión cruzada: A revisa B, B revisa C, C revisa A.

**Pueden programar los tres frentes desde T00**, contra contratos de entradas/salidas acordados. Las dependencias siguientes indican requisitos para verificar/cerrar tareas en AWS. No representan obligación de esperar para escribir el código.

Una rama por frente. B integra cambios en raíces y archivos compartidos. Un operador a la vez por entorno: no ejecutar apply desde tres ramas diferentes contra los mismos estados. El lock S3 no coordina por sí solo código distinto.

## 5. Tareas concretas

Estimaciones de trabajo activo, sin esperas AWS; se ajustan tras T01. Los IDs y contenidos **reemplazan** los del plan anterior.

### T00 — Contrato e interfaces · Todos · 0,5–1 h · Sin dependencias

**Hacer:** adoptar el PDF vigente; acordar carpetas/estados, aliases de los dos providers, SG EC2 común, `instance_ids` por AZ, `ui_node_port`, puertos de acceso, outputs de datos/imágenes y una sola configuración de aplicación para ambos kind. Inventariar estados existentes antes de planear migración.

**Cierre:** cada frente conoce su contrato y qué archivos modifica. Se fijó la interpretación de réplicas por clúster y el orden publish/infra/acceso/app/destroy; se distingue lo heredado de lo nuevo.

### T01 — Viabilidad Lab, acceso y capacidad · B · 1–2 h · T00

**Hacer:** comprobar LabRole/LabInstanceProfile y PassRole; EC2/SSM, ECR, RDS Multi-AZ, Redis réplica, ALB/endpoints/NAT. Verificar restricciones y cuotas de la cuenta real; el PDF indica EC2 hasta large, RDS hasta medium, gp2 hasta 100 GB y Enhanced Monitoring desactivado. Elegir Linux x86_64, tipo con RAM suficiente y versiones compatibles Docker/kind/Kubernetes/Calico. Estimar presupuesto, instalar/verificar herramientas y Session Manager plugin en el operador.

**Cierre:** perfil y servicios disponibles; SSM viable mediante una prueba controlada, o una vía autenticada alternativa definida y documentada si el Lab lo limita. Capacidad justificada, sin asumir que dos t3.medium alcanzan. Sin secretos en Git. No modificar roles preexistentes.

### T02 — Ajustar red y estado existentes · A · 2–4 h · T01

**Hacer:** conservar seis subredes, dos NAT, rutas y endpoints ya declarados. Cambiar privadas a /24 según PDF; revisar si eso reemplaza recursos existentes. Definir SG EC2/ALB y puertos, evitando dependencias circulares entre red y cómputo. Completar bucket real, cifrado, versionado, bloqueo y claves separadas de estado.

**Cierre:** inventario/rutas coherentes, datos sin salida por defecto, NAT de cada zona y endpoints disponibles; bloqueo S3 probado. SG/outputs permiten avanzar cómputo y datos en paralelo. Cualquier reemplazo de subred fue revisado antes de ejecutarse.

### T03 — Dos EC2 con bootstrap kind + CNI · B · 4–6 h · T02

**Hacer:** reemplazar el módulo EKS por cómputo EC2, una por AZ, privadas y con LabInstanceProfile. Automatizar Linux/Docker/kind/kubectl/AWS CLI/SSM, control plane + worker, redes internas y mapeo host:8080→NodePort acordado. Deshabilitar CNI por defecto e instalar Calico; esperar etapas reales de readiness. No ejecutar `local.sh` sin adaptar: instala nginx y aplica objetos fuera de Terraform.

**Cierre:** ambas EC2 sin IP pública, perfil correcto; dos kind separados Ready y CNI operativo. Reinicio recupera servicios base; un segundo paso de preparación no destruye un clúster sano ni requiere preguntas. Fallo de bootstrap produce diagnóstico y no un falso éxito.

### T04 — Terraform administra ambos Kubernetes · B · 3–4 h · T03

**Hacer:** implementar acceso autenticado a las dos API, kubeconfigs privados con CA/certificado validado, aliases y configuración de app separada de infra. Propuesta: dos túneles SSM con puertos locales distintos; scripts con comprobación de destino, estado y limpieza. Sacar autenticación `aws eks get-token`, Helm/LBC y recursos IAM de EKS del camino principal.

**Cierre:** Terraform crea/lee/modifica un objeto de prueba en **cada** contexto y lo elimina; no puede confundir A con B. Puede planear infraestructura sin APIs kind existentes. Si falta un túnel, falla con un mensaje claro antes de operar. Destruir app no elimina EC2.

### T05 — ALB directo a las dos EC2 · A · 2–3 h · T03

**Hacer:** declarar ALB público, SG, listener HTTP/80, target group tipo instance puerto 8080, health check UI y ambos attachments. SG EC2 acepta 8080 solo desde SG ALB. Exportar DNS desde el recurso AWS, no desde un Ingress.

**Cierre:** recursos y targets correctos en el plan; listener/SG/health check coherentes. Los targets pueden estar unhealthy antes de T08; el cierre funcional healthy de ambos es parte de T11. No se instala nginx ni AWS LBC como dependencia.

### T06 — Datos compatibles con el Lab y SG EC2 · A · 2–4 h · T02

**Hacer:** conservar RDS Multi-AZ, Redis replication group, DynamoDB/índice y SQS. Adaptar storage RDS a gp2 ≤100 GB, clase/motores permitidos y Enhanced Monitoring desactivado; comprobar compatibilidad de todas las opciones con la cuenta. SG acepta puertos solo desde SG EC2. Eliminar la política/attachment IAM que intenta crear el módulo actual.

**Cierre:** instancias/replicación y conexiones según PDF, sin acceso público. Primaria/standby de RDS y primaria/réplica Redis en zonas distintas comprobadas en AWS. Prueba de datos desde EC2 y, en T11, desde pods de ambos kind con LabRole. Datos compartidos por ambas copias.

### T07 — Publicar artefactos inmutables · C · 2–4 h · T02

**Hacer:** conservar repos ECR y build amd64 desde el equipo del grupo; separar versión que se publica de versión que se despliega. Preparar v1/v2 con diferencias visibles, tags inmutables y registro de digests. No sobrescribir una versión ni ligar build a `app_version` del despliegue.

**Cierre:** dos juegos de cinco imágenes existen antes de la demo. Seleccionar v1, v2 o v1 otra vez no dispara builds/push. Permisos del usuario para publicar y de EC2 para descargar comprobados por separado.

### T08 — Desplegar dos copias completas y NodePort · C · 3–5 h · T04, T06, T07

**Hacer:** reutilizar el módulo de aplicación con provider A/B; dos réplicas por servicio en cada kind. UI NodePort y mapeo idéntico al bootstrap, sin Ingress/spread entre AZ. Automatizar desde las EC2 la descarga con LabRole y carga a containerd de nodos kind antes de actualizar Deployments. Revisar requests, probes, rolling update y margen de memoria. Cart/Orders deben funcionar con credenciales temporales del perfil, no con credenciales del usuario.

**Cierre:** diez pods app Ready por clúster; misma versión/digest esperado, DB reales y UI accesible por cada target. Una versión antes no cacheada se carga y despliega en ambos. No hay compilación en las EC2 ni necesidad de editar YAML a mano.

### T09 — Policies y cuarentena en ambos kind · C · 2–4 h · T08

**Hacer:** tráfico específico UI→Catalog/Cart/Checkout y Checkout→Orders, ingreso UI compatible con SNAT/NodePort y SG exterior. Eliminar permiso genérico backend→backend. Cambiar NetworkPolicies con `quarantine`, sin cambiar etiquetas del PodTemplate ni reiniciar Deployments.

**Cierre:** positivos/negativos verificados por clúster. Checkout pierde entrada/salida a servicios, Redis, DNS e Internet; catálogo/carrito siguen. La reversión restaura compra. El plan muestra cambios de policies y no reemplazo de pods; capturar UID/restartCount antes/después para comprobarlo. Ningún allow alternativo anula el aislamiento.

### T10 — Preparar arnés y evidencia · B coordina, A/C aportan · 2–4 h por frente · T00

**Hacer:** adaptar `verificar.sh` para dos contextos kind y ALB; precondiciones y herramientas, JSON con jq, timeouts, cleanup de sondas y resultados por contexto. No considerar éxito cualquier error distinto de timeout. Una sonda negativa solo vale si arrancó, conoce el destino y tiene su herramienta. Integrar Cypress para flujo completo y correlacionar compra, orden y evento SQS nuevos.

**Cierre:** falta de herramienta, API inaccesible, pod de prueba fallido o target roto producen error. Hay pruebas de red, credenciales, persistencia y rollback, no solo estado Running. Se prepara desde el inicio y se ejecuta de verdad en T11.

### T11 — Integración y pruebas completas · Todos · 2–4 h de sesión · T05, T09, T10, T15

**Hacer:** integrar ramas; formato/validate por raíz y plan revisado. Usar el Apply de T15 para crear infra, validar artefactos existentes, preparar acceso y aplicar app. Probar directamente kind A, kind B y la URL ALB. Completar pruebas de datos/credenciales y ambos targets healthy. Segundo plan para verificar convergencia. T15 comprueba la automatización; T11 conserva las pruebas completas de aplicación, navegador y persistencia.

**Cierre:** veinte pods app Ready, compra real desde ambas copias, datos persistentes al recrear pods, orden/evento identificables, targets sanos y policies efectivas. Los planes de infra, imágenes y app terminan sin cambios tras estabilizar. Las reglas de SG y rutas se comprueban además del HTTP 200.

### T12 — Cuatro casos de uso corregidos · Todos · 3–5 h de sesión · T11

**Hacer:** (1) cambiar manualmente un recurso AWS desde consola, plan detecta drift y apply lo revierte; (2) UI 2→4→2 en ambos kind, sin agregar EC2 ni nodos; (3) `app_version` v1→v2→v1 desde ECR, sin builds; (4) `quarantine=["checkout"]` y reversión con cambios de policies en ambos.

**Cierre:** evidencia en las dos copias, baseline restaurado y plan=0 entre casos. Campaña: 12 pods app por kind, 24 total; cuenta de EC2 sigue en 2. Rollout/rollback mantiene UI respondiendo según sondeo continuo por copia y ALB, y vuelve al digest anterior. Cuarentena corta compra en ambas y preserva catálogo/carrito. La propuesta nueva no exige un número exacto de recursos por plan: no conservar esa restricción del documento anterior.

### T13 — Destroy ordenado y recreación · Todos, A coordina · 2–4 h de sesión · T12

**Hacer:** usar Destroy de T15 con túneles y EC2 vivas para retirar aplicación en ambos kind y verificar objetos eliminados; luego retirar infra AWS. Conservar ECR/artefactos para la recreación y documentar su retención. Auditar por IDs/tags: ALB/targets, EC2/EBS, endpoints/ENI, NAT/EIP, SG, datos y repositorios. Recrear desde estados app/infra vacíos con Apply; repetir smoke/E2E y limpiar al cerrar la sesión. La eliminación de ECR requiere un ciclo aparte expresamente acordado.

**Cierre:** no quedan recursos del POC huérfanos; retenciones documentadas: bucket/estado, ECR/artefactos para recreación y LabRole/LabInstanceProfile preexistentes. No se borran estos IAM. Recreación reproducible. Persistencia se exige ante reinicios de pods, no después de borrar las bases con destroy.

### T14 — How-to, informe, PPT y ensayo · Todos · 2–3 h por persona + ensayo · T13

**Hacer:** A explica red/datos/ALB, B EC2/kind/acceso/estados y C artefactos/app/policies. Actualizar README, decisiones, guía y guion; identificar PDF vigente. Documentar secrets/variables, operación Actions, renovación del Lab, retención y recuperación tras fallos. Preparar informe final, PPT real, evidencia y video de respaldo, enlace GitHub accesible. El borrador se escribe en paralelo desde T00.

**Cierre:** otro integrante reproduce todos los pasos; no hay comandos/credenciales/configuraciones ocultos. Ensayo de los tres <30 minutos, con demo funcional y limitaciones de capacidad explicadas. Entrega Campus antes del 4/11, 23:59.

### T15 — GitHub Actions: Plan, Apply y Destroy · B coordina, A/C revisan · 4–6 h + ciclo AWS · T02, T04, T07, T08, T09, T10

**Hacer:** tres workflows manuales desde `main`, con los tres secrets temporales del Lab, cuenta/región/backend explícitos, herramientas fijadas y un grupo de concurrencia común. Reutilizar los scripts existentes mediante un orquestador compartido. Plan no crea infraestructura ni precarga imágenes; si faltan kind o caché, informa la fase app pendiente. Apply planifica y aplica por fases, espera bootstrap, verifica ECR, precarga y opera ambos kind en la misma sesión SSM. Destroy retira app antes de EC2 y conserva bucket, ECR/artefactos e IAM preexistente. No intercambiar planes de aplicación entre runs ni publicar estados, kubeconfigs o planes sensibles. Ver [alcance y aceptación T15](automatizacion-t15.md).

**Cierre:** ciclo real desde runner limpio: plan sin mutaciones del entorno, apply completo y segundo plan convergente, destroy auditado e idempotente. Rechazo ante credenciales vencidas, cuenta/backend equivocados, artefacto ausente y un túnel caído; ese fallo impide retirar infra con app pendiente. Resúmenes sanitizados con resultados por fase y enlaces públicos. Documentación reproducible para configurar los secrets y renovar la sesión.

**Estimación:** 4–6 h de desarrollo y pruebas locales, más aproximadamente 1–2 h de ciclo AWS con esperas. El ciclo puede aportar evidencia a T11/T13, pero no sustituye sus criterios de cierre. T14 puede avanzar en paralelo. La tarea está **planificada**, no implementada.

## 6. Mapa y dependencias

Mapa interactivo: [mapa-de-tareas.html](mapa-de-tareas.html). Las dependencias son para cerrar/pruebas; el desarrollo puede empezar en paralelo tras T00.

```text
T00 → T01 Lab → T02 Red y estado
T02 → T03 EC2 + kind + CNI → T04 Acceso Terraform
T03 → T05 ALB directo
T02 → T06 Datos       (en paralelo al cómputo)
T02 → T07 Imágenes    (en paralelo al cómputo)
T04 + T06 + T07 → T08 Aplicación en ambos kind → T09 Policies
T00 → T10 Preparar pruebas
T02 + T04 + T07 + T08 + T09 + T10 → T15 GitHub Actions
T05 + T09 + T10 + T15 → T11 Integración
                → T12 Cuatro casos
                → T13 Destroy + recreación
                → T14 Entrega y ensayo final
```

Ruta pendiente: **T15 → T11 → T12 → T13 → cierre T14**. El borrador T14 y la preparación local del arnés T11 pueden avanzar mientras se implementa T15; los ciclos que mutan el entorno AWS se serializan. El lock por estado S3 no sustituye la coordinación entre ejecuciones locales y Actions.

## 7. Matriz mínima de pruebas

| Área | Evidencia exigida |
|---|---|
| Estática | fmt/validate por configuración, Bash y plan revisado; sin cambios después de estabilizar |
| Red | Seis subredes con CIDR correctos, NAT/rutas por AZ, datos aislados, endpoints y SG |
| Cómputo/acceso | Dos EC2 privadas con perfil existente; dos kind Ready; providers realmente apuntan a clústeres diferentes |
| CNI | Permiso y bloqueo funcionales en cada kind; objetos NetworkPolicy existentes por sí solos no alcanzan |
| Entrada pública | ALB tipo application creado por Terraform, targets instance:8080 y health check sano de ambas copias |
| Artefactos/IAM | Una versión nueva para la caché se carga con LabRole en los dos kind; Cart/Orders acceden con credenciales temporales |
| Compra y datos | Orden nueva y evento SQS correlacionados; carrito/checkout/orden sobreviven a recreación de pods; revisar desde ambas copias |
| Escala | UI 2→4→2 por kind; 20→24→20 pods app totales, sin sumar EC2 ni memoria física |
| Versión | UI accesible por copia y ALB durante v1→v2→v1; digest original recuperado sin build/push |
| Cuarentena | Entrada/salida de Checkout bloqueadas en ambos; catálogo/carrito funcionan; UID de pods estable; recuperación al vaciar lista |
| Ciclo completo | Destroy app en ambos primero, después AWS; auditoría de huérfanos y recreate + pruebas |

No probar solo detrás del ALB: podría esconder un kind roto. No aceptar que una compra cualquiera preexistente pruebe persistencia. No usar un error de DNS/herramienta como evidencia suficiente de un bloqueo de red. Registrar fecha, commit, contexto, estímulo y resultado; excluir credenciales, kubeconfigs, tfstate y planes binarios de Git.

La configuración Multi-AZ se comprueba mediante topología/estado de RDS y Redis. Un ensayo real de failover puede agregarse si el tiempo y el Lab lo permiten; no es un quinto caso de uso requerido.

## 8. Calendario propuesto

**Calendario original, no previsión vigente.** Al 4/11 faltan T11–T14 y se agrega T15. T15 suma 4–6 h de trabajo más el ciclo AWS; no asumir que entra en el margen original. Priorizar la automatización mínima del POC y adelantar T14 en paralelo.

| Fecha | Resultado |
|---|---|
| **29/10** | T00/T01, estado y contratos. Prueba temprana de kind+CNI, memoria, SSM y credenciales. Abrir tres frentes. |
| **30/10** | Red/datos reutilizados; bootstrap y acceso; artefactos v1/v2. Arnés en paralelo. |
| **31/10** | Dos copias funcionando por target; integrar ALB y cerrar policies. |
| **1/11** | T11: pruebas completas por clúster y ALB; iniciar cuatro casos. |
| **2/11** | Cerrar casos y ciclo destroy/recreate con evidencia. |
| **3/11** | How-to/informe/PPT, revisión cruzada y ensayo completo. |
| **4/11** | Margen para correcciones y entrega antes de 23:59. |

## 9. Referencias técnicas para implementar

- [Configuración de kind](https://kind.sigs.k8s.io/docs/user/configuration/): API, CIDR y correspondencia entre containerPort del mapeo y nodePort del Service.
- [Calico sobre kind](https://docs.tigera.io/calico/latest/getting-started/kubernetes/kind): CNI por defecto deshabilitado y red de pods configurada; usar versiones compatibles fijadas.
- [Registros privados en kind](https://kind.sigs.k8s.io/docs/user/private-registries/): precarga desde el host como vía soportada para registros privados; descargar al host no carga automáticamente containerd de los nodos.
- [Session Manager: iniciar sesiones y port forwarding](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html): mecanismo propuesto para operar EC2 privadas, sujeto a permisos y agente del Lab.
- [NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/): permisos aditivos y necesidad de un plugin que aplique las políticas.
- [Secrets de GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets) y [concurrencia de despliegues](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments): configuración de las tres operaciones T15.

La ampliación T15 actualiza la planificación; no instala workflows ni configura secrets. El estado y la evidencia de T00–T10 se registran en [estado-tareas.md](estado-tareas.md).
