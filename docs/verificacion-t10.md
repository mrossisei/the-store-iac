# T10 — Arnés de pruebas y evidencia

`verificar.sh` ahora requiere configuración explícita de ambos kind. No consulta EKS ni modifica el kubeconfig del operador. Python analiza respuestas JSON estructuradas; jq está entre las precondiciones para revisar los reportes, sin extraer valores con grep/cut. Las dos identidades se validan antes de ejecutar pruebas de aplicación o recrear pods. Cada comando tiene tiempo límite y el reporte final devuelve código 1 si cualquier comprobación o limpieza falla.

```bash
cp config/verificacion.example.json .local/verificacion.json
# Completar kubeconfigs/contextos y URLs de ambas copias; T04 prepara accesos.
./verificar.sh --config .local/verificacion.json --mode bootstrap --report .local/bootstrap.json
./verificar.sh --config .local/verificacion.json --mode app --report .local/baseline.json
jq '{status,results}' .local/baseline.json
```

bootstrap verifica dos nodos Ready por kind, Calico desplegado, kindnet ausente y UID de kube-system distinto en A/B. app agrega réplicas exactas Ready, acceso HTTP directo a ambas copias, caminos permitidos y pod intruso bloqueado, credenciales temporales LabRole obtenidas por IMDSv2 desde Carts/Orders, HTTP del ALB y **ambos** targets healthy. Los IDs esperados del target group son explícitos, no basta con que un target cualquiera responda.

Las sondas prueban el proceso de origen por loopback y cada PodIP de destino Running, incluso si pierde readiness en puerto 8080, sin depender de endpoints del Service. UI usa curl; Checkout usa HTTP de Node con timeout total. Solo curl=28 con HTTP=000 o timeout explícito de Node demuestra bloqueo; DNS roto, exec fallido, herramienta ausente y conexión rechazada fallan. El pod intruso usa la imagen configurada de UI con imagePullPolicy Never, curl y sleep: si la imagen o herramienta no está disponible, falla explícitamente. Tiene nombre único, sin labels app, y se elimina aun si falla su arranque. No se considera Running equivalente a Ready.

## Compra, IAM y persistencia

Instalar las dependencias existentes de E2E con su yarn.lock (Node >=20 y dependencias del sistema requeridas por Cypress):

```bash
cd the-store/src/e2e
npx --yes --package=yarn@1.22.22 yarn install --frozen-lockfile
env -u ELECTRON_RUN_AS_NODE ./node_modules/.bin/cypress verify
cd ../../..
./verificar.sh --config .local/verificacion.json --mode full --restart-for-persistence --report .local/full/report.json
```

full ejecuta la spec tp-compra.cy.js separadamente contra A y B. Usa email único, añade un producto y comprueba el total y el ID mostrado por la UI. Antes lee IDs existentes en Orders desde Checkout con Node, exigiendo HTTP 200 y JSON válido; después exige un ID **nuevo**, con el mismo email y un evento SQS cuyo order.id coincide (estructura real de OrderCreatedEvent). No acepta una orden cualquiera ni un aumento aproximado del tamaño de cola. Los mensajes observados no se borran; se ocultan como máximo 60 segundos mientras se busca y se restaura su visibilidad al terminar. El plazo contempla los 10 segundos de delay del productor. Ejecutar en una sesión de pruebas sin otro consumidor de SQS: una cola con backlog grande o un consumidor puede hacer que no se observe el evento dentro del plazo y el resultado debe ser FAIL.

Con --restart-for-persistence se recrea Carts con el mismo carrito/cookies antes de pagar y se verifica que conserva el producto; después de comprar se recrean Carts/Checkout/Orders y se consulta el ID persistente. Esa opción modifica pods, explícitamente; no es la prueba de cuarentena. La persistencia específica del estado intermedio de Checkout/Redis queda para la integración T11, además de estas pruebas de carrito/orden. Sin la opción no se atribuye éxito a pruebas de recreación.

El chequeo de IMDSv2 procesa token/credenciales solo en memoria y no los escribe al reporte. Rechaza variables AWS de claves estáticas en el PodSpec. La compra y el evento complementan esa prueba al ejercitar DynamoDB, RDS y SQS por la aplicación; leer STS en el operador no sustituye acceso desde pods.

## Demos y comparaciones

Los reportes guardan por contexto UID de clúster, UID/restarts/digests de contenedores, imágenes deseadas y digests reales por servicio. Para comparar después de una intervención:

```bash
# Cuarentena: completar quarantine:["checkout"] en el JSON de pruebas.
./verificar.sh --config .local/verificacion.json --mode app --compare .local/baseline.json --expect unchanged --report .local/quarantine.json
# Tras volver a la versión inicial:
./verificar.sh --config .local/verificacion.json --mode app --compare .local/baseline.json --expect rollback --report .local/rollback.json
```

quarantine cambia las expectativas de UI→Checkout y Checkout→Orders a timeout, conservando UI→Catalog/Carts. unchanged exige los mismos UID, reinicios e imágenes de todos los pods de aplicación (excluye las sondas propias). rollback exige las referencias y los digests de ejecución originales; rollout exige nuevas imágenes y pods. El conteo de réplicas se adapta con replicas en el JSON de pruebas. Las comprobaciones específicas de DNS/Internet/datos para la cuarentena se completan con los destinos concretos de T06/T09; esta preparación no declara probadas esas políticas futuras.

## Evidencia y límites actuales

Las regresiones locales del arnés comprueban: errores DNS/exec/herramienta no cuentan como bloqueo, Running sin readiness y conteos extra fallan, se detectan reinicios/cambio de clúster/rollback incorrecto, y una sonda fallida se conserva para limpieza. Syntax Bash/Python/JavaScript aprobada. Los reportes, recibos y logs van en .local/ con permisos privados, fuera de Git.

**T10 queda preparada.** Esta revisión local no ejecutó compra, persistencia, cuarentena ni rollback en el entorno final; su ejecución corresponde al operador. Se ejecutan de verdad en T11/T12; si faltan recursos, herramientas, permisos o acceso, el arnés debe fallar y no omitirlos como PASS.

Referencias: [Node events de Cypress](https://docs.cypress.io/api/node-events/overview), [cy.task](https://docs.cypress.io/api/commands/task).

Al verificar T03 se ejecutó además el modo bootstrap contra las dos API reales mediante SSM/TLS. Pasó con clústeres diferentes; los controles con contextos duplicados y API inaccesible fallaron como se esperaba. `scripts/probar-apis.py` reproduce esa prueba temporal y limpia túneles/kubeconfigs. Esto no sustituye el modo app/full de T11.
