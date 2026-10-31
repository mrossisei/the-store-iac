# T10 — Arnés de pruebas y evidencia

`verificar.sh` ahora requiere configuración explícita de ambos kind. No consulta EKS ni modifica el kubeconfig del operador. Python analiza respuestas JSON estructuradas; jq está entre las precondiciones para revisar los reportes, sin extraer valores con grep/cut. Cada comando tiene tiempo límite y el reporte final devuelve código 1 si cualquier comprobación o limpieza falla.

```bash
cp config/verificacion.example.json .local/verificacion.json
# Completar kubeconfigs/contextos y URLs de ambas copias; T04 prepara accesos.
./verificar.sh --config .local/verificacion.json --mode bootstrap --report .local/bootstrap.json
./verificar.sh --config .local/verificacion.json --mode app --report .local/baseline.json
jq '{status,results}' .local/baseline.json
```

bootstrap verifica dos nodos Ready por kind, Calico desplegado, kindnet ausente y UID de kube-system distinto en A/B. app agrega réplicas exactas Ready, acceso HTTP directo a ambas copias, caminos permitidos y pod intruso bloqueado, credenciales temporales LabRole obtenidas por IMDSv2 desde Carts/Orders, HTTP del ALB y **ambos** targets healthy. Los IDs esperados del target group son explícitos, no basta con que un target cualquiera responda.

Las sondas negativas usan ClusterIP/puerto obtenidos de la API, un pod que alcanzó Ready y curl verificado. Solo curl=28 con HTTP=000 demuestra timeout; DNS roto, exec fallido, comando ausente y conexión rechazada fallan. Los caminos permitidos prueban también curl contra el loopback del proceso. El pod intruso tiene nombre único, sin labels app que lo incluyan en los Services, y se elimina aun si falla su arranque. No se considera Running equivalente a Ready.

## Compra, IAM y persistencia

Instalar las dependencias existentes de E2E con su yarn.lock (Node >=20 y dependencias del sistema requeridas por Cypress):

```bash
cd the-store/src/e2e
npx --yes --package=yarn@1.22.22 yarn install --frozen-lockfile
./node_modules/.bin/cypress verify
cd ../../..
./verificar.sh --config .local/verificacion.json --mode full --restart-for-persistence --report .local/full/report.json
```

full ejecuta la spec tp-compra.cy.js separadamente contra A y B. Usa email único, añade un producto y comprueba el total y el ID mostrado por la UI. Antes lee IDs existentes en Orders desde Checkout; después exige un ID **nuevo**, con el mismo email y un evento SQS cuyo order.id coincide (estructura real de OrderCreatedEvent). No acepta una orden cualquiera ni un aumento aproximado del tamaño de cola. Los mensajes observados no se borran; se ocultan como máximo 60 segundos mientras se busca y se restaura su visibilidad al terminar. El plazo contempla los 10 segundos de delay del productor. Ejecutar en una sesión de pruebas sin otro consumidor de SQS: una cola con backlog grande o un consumidor puede hacer que no se observe el evento dentro del plazo y el resultado debe ser FAIL.

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

El 31/10/2026 pasaron los tests locales del arnés: errores DNS/exec/herramienta no cuentan como bloqueo, Running sin readiness y conteos extra fallan, se detectan reinicios/cambio de clúster/rollback incorrecto, y una sonda fallida se conserva para limpieza. Syntax Bash/Python/JavaScript aprobada. Los reportes, recibos y logs van en .local/ con permisos privados, fuera de Git.

**T10 queda preparada.** App/ALB/datos todavía no existen en T03, por lo que no se afirma haber ejecutado compra, persistencia, cuarentena o rollback en el entorno final. Se ejecutan de verdad en T11/T12; si faltan recursos, herramientas, permisos o acceso, el arnés debe fallar y no omitirlos como PASS.

Referencias: [Node events de Cypress](https://docs.cypress.io/api/node-events/overview), [cy.task](https://docs.cypress.io/api/commands/task).
