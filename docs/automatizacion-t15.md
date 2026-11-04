# T15 — Operar el POC desde GitHub Actions

Estado: **pospuesta, sin workflows implementados ni secrets configurados por esta revisión**. Pedido inicial del usuario del 4/11/2026; luego se priorizó una sola sesión AWS para T11/T12 y la entrega. El diseño original de abajo se conserva, pero T15 no bloquea T11 ni exige recrear infraestructura durante esta campaña. No cambia la arquitectura de la preentrega. Depende de T02, T04, T07, T08, T09 y T10. B coordina; A revisa estados/destroy y C artefactos/app.

Estimación: **4–6 h de desarrollo y pruebas locales + aproximadamente 1–2 h de ciclo real AWS**, sujeto a permisos y sesión del Lab. Parte del ciclo puede reutilizarse en T11/T13; no elimina sus pruebas de navegador, persistencia, casos y recreación.

## Referencia revisada y diferencias

Referencia local: `cloud/2026Q2-G5/.github/workflows/{plan,deploy,destroy}.yml`, `scripts/terraform-actions.py` y su README. No se modifica ese proyecto.

Los workflows revisados usan un runner Ubuntu, credenciales temporales por secrets, permisos `contents: read`, concurrencia compartida y ejecución manual para apply/destroy. Plan también se dispara con push a main. El helper Python contiene validación de cuenta/backend, planes efímeros y resúmenes; **es un diseño de referencia y no está invocado por esos tres YAML**. No copiar supuestos de ambos caminos como si fueran una implementación única.

Este repo tiene tres estados remotos, dos API Kubernetes privadas y planes de app con paths/certificados de una sesión SSM. Un runner nuevo no tiene Docker local con las imágenes de recuperación. Adaptar el orden y las precondiciones; no basta reemplazar `infra` por `terraform/` en el ejemplo.

## Entregables y configuración

- `.github/workflows/plan.yml`, `apply.yml` y `destroy.yml`, todos con `workflow_dispatch`. Operaciones AWS desde `main`; apply/destroy manuales con confirmación de operación. No ejecutar despliegues desde PR ni activar un plan AWS en cada push para este alcance mínimo.
- Un orquestador compartido, por ejemplo `scripts/terraform-actions.py`, que reutilice `estado.py`, los guards T04/T08 y los validadores existentes. La lógica no se duplica en tres YAML.
- Runner Ubuntu con versión explícita, Terraform y herramientas compatibles con `config/herramientas.json`, AWS CLI, Session Manager plugin, Python, kubectl y dependencias necesarias. Actions fijadas por SHA revisado. No requiere runner dentro de la VPC: SSM es el acceso a kind.
- Secrets del repositorio: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`. Renovar juntos cuando venza el Learner Lab. Configurarlos de forma privada; nunca imprimirlos, incluirlos en tfvars ni pasarlos a pods. No crear roles nuevos para OIDC en esta tarea.
- Variables no secretas: `AWS_ACCOUNT_ID` esperada, `AWS_REGION` y `TF_STATE_BUCKET`; contrastarlas con `config/entorno.json`. Conservar las claves S3 existentes de infra/imagenes/aplicacion, cifrado, versionado y lock. No crear estados alternativos por run/branch ni tocar la raíz histórica EKS `terraform/`.
- Un mismo grupo de concurrencia para las tres operaciones, independiente del nombre del workflow, con `cancel-in-progress: false`. Mantener locks S3 y coordinar además las operaciones locales; la concurrencia de GitHub no bloquea un apply desde una laptop ni convierte las tres raíces en una transacción.

## Plan: diagnóstico sin mutaciones del entorno

1. Comprobar secrets presentes y STS válido, cuenta esperada, región, bucket/propiedad y configuración antes de Terraform. Un fallo aborta sin mostrar valores sensibles.
2. Inicializar las raíces implementadas con el backend existente y ejecutar fmt/validate. Plan no crea/adopta bucket ni repositorios, construye imágenes o levanta infraestructura. El bloqueo normal del backend puede crear/retirar su lock transitorio.
3. Planear infra e imágenes. Cuando ambas EC2/kind y los digests precargados estén disponibles, abrir acceso T04 y planear app con los guards de solo lectura. **No invocar directamente `aplicacion.py plan`: hoy precarga imágenes y por eso debe adaptarse o usarse el camino de solo lectura con `acceso.py`.**
4. Con entorno apagado, informar los planes AWS y la fase app como **pendiente de Apply**, nunca como una validación completa exitosa. Diferenciar infraestructura ausente de credenciales inválidas, túnel roto o drift que deja una app administrada inaccesible: estos últimos son errores explícitos.
5. Publicar solo resumen sanitizado por raíz y estado de cada fase. El Plan independiente es diagnóstico: **Apply vuelve a planificar** sobre el mismo commit y la realidad actual. No promete aplicar el binario producido por otro run.

## Apply: una sesión completa desde runner limpio

1. Validar identidad, estados existentes y manifiestos ECR de la versión seleccionada. Exigir que las catorce imágenes conservadas necesarias para las versiones registradas sigan disponibles con sus digests. Ante reset del Lab o falta de artefactos, fallar con instrucciones de T07/T08; no fabricar tags equivalentes ni depender de la caché del desarrollador.
2. Verificar el backend existente. La creación/recuperación del bucket es un procedimiento de bootstrap separado y explícito; no recrear silenciosamente un backend desaparecido mientras haya recursos o estados por reconciliar.
3. Revisar y aplicar solo los planes permitidos de imágenes/infra; esperar EC2, agente SSM, bootstrap y readiness de los dos kind con timeout acotado. Usar una comprobación adecuada para despliegue; no ejecutar por defecto los ensayos destructivos/reboot de T03.
4. Abrir ambos túneles mediante el wrapper existente. Precargar por digest con LabRole en los cuatro nodos; revisar y aplicar el plan app **dentro de esa misma sesión**. No transferir kubeconfigs, certificados o planes de app entre jobs o runs.
5. Verificar veinte pods Ready y ambos targets ALB; ejecutar smoke por copia y entrada pública. Generar planes de convergencia por raíz. Las pruebas E2E completas y de persistencia siguen perteneciendo a T11.
6. Publicar únicamente URL pública, commit, cuenta/región, conteos y resultados sanitizados. Cerrar túneles y retirar material temporal incluso ante fallo/cancelación manejable. Con apply parcial, conservar estado y explicar cómo reintentar; no ejecutar destroy automático como limpieza de un error.

## Destroy: aplicación antes que infraestructura

1. Comprobar identidad y que se leen los estados correctos; backend inaccesible no equivale a entorno vacío. Inventariar IDs propios para la auditoría final. No crear backend durante destroy.
2. Si app administra recursos, abrir y verificar ambos accesos, revisar/aplicar su plan de destrucción y comprobar namespace ausente en ambos kind y estado app vacío. Si un túnel falla o kind está inaccesible con app pendiente, detenerse **antes** de eliminar EC2; documentar recuperación, sin borrar recursos del estado para ocultar el fallo.
3. Solo con app vacía, planear y retirar infra AWS. En un entorno ya vacío, permitir repetición sin intentar abrir túneles contra hosts eliminados.
4. Auditar IDs/tags de recursos retirados y estados app/infra vacíos. Conservar **bucket/versiones de estado, ECR con sus artefactos y LabRole/LabInstanceProfile preexistentes**. Retirar ECR o perder su contenido rompe el próximo Apply; no incluir su destroy en la operación normal.
5. Mostrar resumen de la auditoría y recursos conservados. Los datos administrados se eliminan con infra; la retención ECR no significa retención de RDS/Redis/DynamoDB/SQS.

## Planes, logs y material sensible

Los planes binarios/JSON pueden contener contraseñas SQL y valores previos del estado; `sensitive` no cifra esos archivos. Mantenerlos efímeros, con permisos privados, dentro del runner y eliminarlos al cerrar. No subirlos como artifacts/cache ni publicar el contenido de `.local`, estados, kubeconfigs, claves, outputs sensibles o logs completos de SSM. El resumen se construye con una lista explícita de campos permitidos; no confiar solo en el enmascarado de secrets de GitHub.

Aprovechar los logs privados existentes para revisar fallos dentro del job, pero no convertir su volcado indiscriminado en salida pública de Actions. Fijar timeouts de job/comando y limpieza `always` además del cierre del wrapper; reconocer que una terminación forzosa puede dejar sesiones remotas hasta su timeout. Probar ese comportamiento sin cerrar sesiones ajenas.

## Criterios de cierre

- Validación local de YAML/scripts y casos relevantes del orquestador: orden, identidad/backend, estado vacío, credenciales vencidas, artefacto ausente, fallo de bootstrap y acceso B caído. Revisar que ningún error se transforme en un resultado completo exitoso.
- Ejecuciones reales desde GitHub: Plan con infra apagada y app declarada pendiente; Apply desde runner limpio; smoke A/B/ALB; nuevo Plan convergente; Destroy ordenado, auditado y repetible sin pérdida de ECR/estado.
- Evidencia de que Plan no aplica ni precarga, que Apply recrea su plan en su propia sesión, que los workflows comparten grupo de concurrencia y que un fallo de acceso impide retirar infra con app pendiente.
- Registrar run IDs/commit y evidencias sanitizadas; revisar logs y artifacts para comprobar que no se publicaron secretos/certificados/planes. Actualizar how-to, estado de tareas y mapa. Commit, push y merge a main al cerrar T15.

## Dependencias y alcance de esta revisión

```text
T02 + T04 + T07 + T08 + T09 + T10 → T15
T05 + T09 + T10 + T15 → T11 → T12 → T13 → cierre T14
T14: borrador en paralelo con T15/T11/T12
```

Esta revisión incorpora la tarea y el diseño; no operó AWS, no creó workflows ni cargó secrets. T15 permanece pendiente hasta cumplir los criterios anteriores.

Referencias oficiales: [secrets de GitHub](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets), [concurrencia y despliegues](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments), [planes guardados de Terraform](https://developer.hashicorp.com/terraform/cli/commands/plan).
