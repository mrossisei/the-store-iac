# T06 — Datos compartidos para los dos kind

La raíz `terraform/infra` incorpora `modules/datos`: RDS MySQL para Catalog, RDS PostgreSQL para Orders, Redis para Checkout, la tabla DynamoDB de Cart con su índice y SQS para eventos de Orders. Ambas copias de la aplicación consumen los mismos recursos.

`config/herramientas.json` fija MySQL 8.4.11, PostgreSQL 17.11, clase RDS `db.t3.micro`, Redis 7.1 y `cache.t3.micro`. Se consultaron las opciones gp2/Multi-AZ de esos motores/clase en us-east-1. MySQL 8.0.46 aparecía en Describe pero su creación con Extended Support desactivado fue rechazada: la cuenta exige ese soporte para 8.0 después del 31/07/2026. Se eligió 8.4.11 para mantener soporte estándar; leer metadatos no se presenta como permiso de creación.

Las RDS usan 20 GiB gp2 cifrados, Multi-AZ y subredes de datos sin salida a Internet, sin acceso público, Enhanced Monitoring ni Performance Insights. No se configura un rol de monitoring. Las contraseñas alfanuméricas se generan con `random_password`; se conserva el esquema de bases/usuarios `catalogdb/catalog` y `orders/orders`. Actualizaciones menores automáticas desactivadas para mantener las versiones comprobadas.

Redis tiene dos nodos, primaria/réplica en las AZ a/b, Multi-AZ y failover habilitados, y cifrado en reposo. Conserva el protocolo privado Redis:6379 de la aplicación; no requiere cambios a `redis://` del contrato. El SG de datos acepta solamente TCP/3306, 5432 y 6379 desde el SG EC2; no acepta CIDR público/VPC ni SG ALB. El módulo no declara políticas ni attachments IAM: DynamoDB/SQS se prueban con LabRole existente. `node_role_name` se conserva solo como entrada histórica sin uso; no aplicar la raíz EKS antigua.

## Crear y comprobar

Con backend y credenciales vigentes:

```bash
umask 077
terraform -chdir=terraform/infra init
terraform -chdir=terraform/infra plan -out=../../.local/infra.tfplan
terraform -chdir=terraform/infra apply ../../.local/infra.tfplan
python3 scripts/probar-datos.py
terraform -chdir=terraform/infra plan -detailed-exitcode
```

Desde infra vacía son 62 recursos, 13 del módulo de datos (dos son contraseñas aleatorias, no recursos AWS). El bootstrap kind tiene su propio verificador T03. RDS puede informar `available` mientras todavía convierte a Multi-AZ: la sonda espera hasta 15 minutos a que AWS informe la standby y luego exige ambas AZ reales. No imprimir `terraform output -json` completo: `databases` es sensible y JSON puede revelar passwords aunque estén ocultos en la salida habitual. Consultar individualmente `database_endpoints` o `data_resources` para diagnóstico sin credenciales.

El user-data de cómputo recibe solo las ocho claves de bootstrap kind/Kubernetes/Calico; versiones de motores y herramientas del operador quedan fuera. Así cambiar una versión de RDS no reemplaza accidentalmente ambos hosts y sus clústeres.

`databases` conserva los siete campos sensibles del contrato (`mysql_host`, `mysql_password`, `postgres_host`, `postgres_password`, `redis_host`, `dynamodb_table`, `sqs_queue_url`). `database_endpoints` conserva el mapa sin passwords y `data_resources` agrega IDs, grupos de subredes/SG y endpoint lector Redis para auditar la topología. T08 consume la conexión sensible sin publicar secretos.

## Qué prueba la sonda real

`scripts/probar-datos.py` comprueba por API RDS available, versiones/clase, gp2 acotado/cifrado, privacidad, SG/subredes y primaria/standby en AZ diferentes. Contrasta Redis available, primaria/réplica en AZ distintas, tipo de nodos y failover. Valida claves/índice DynamoDB y existencia de SQS.

Instala drivers de prueba fijados en un venv privado por EC2, con Python 3.11 separado del Python de sistema. Cada proceso exige credenciales de instancia (`iam-role`) y ARN de LabRole. MySQL y PostgreSQL validan certificado y hostname con el bundle oficial de RDS; no desactivan TLS ni modifican roles IAM. Los passwords viajan en un objeto temporal S3 cifrado y versionado que los hosts descargan con LabRole; no se incrustan en Run Command ni se imprimen.

La EC2 A escribe filas/clave/ítem/mensaje exclusivos de la ejecución. B los lee, consulta el GSI, comprueba el lector Redis y escribe su respuesta. A vuelve a leer los datos de B. Las fases separadas demuestran datos compartidos entre hosts; no se toma una conexión TCP como prueba de persistencia. Son pruebas desde EC2, no desde pods: la integración de Cart/Orders y el flujo completo siguen en T08/T11.

Las tablas tienen PK y comentario de propiedad; los nombres se validan y los valores usan parámetros. Las transacciones SQL terminan antes de llamar a otros servicios y PostgreSQL tiene límites de sentencia/lock. La limpieza exige la propiedad antes de borrar tablas/ítems/claves. Solo se reciben y eliminan mensajes SQS de la ejecución; cualquier mensaje ajeno recupera visibilidad y no se purga la cola.

El `finally` intenta retirar sondas y configuración privada de ambos hosts, el archivo local de conexión y las versiones exactas del objeto S3, incluso ante una respuesta de upload perdida. Un delete marker de S3 no cuenta como eliminación de un secreto versionado. No se eliminan otras keys ni versiones del estado. Si falta una comprobación o la limpieza falla, el reporte no es PASS. Reportes/logs privados quedan en `.local/t06/`; contienen resultados y diagnósticos sin mostrar credenciales.

## Retirar datos

Primero retirar aplicación con acceso a ambos kind y comprobar que terminaron las pruebas de datos/imágenes. Después revisar/aplicar destroy de infra. Para esta POC se desactivan backups automáticos, snapshot final RDS y retención de snapshots Redis; destruir elimina los datos de demostración. No usar esta política como respaldo de una aplicación con datos que deban conservarse.

Auditar RDS/Redis, tabla/cola, SG/grupos de subredes y los recursos de red/cómputo/ALB por sus IDs. Conservar el bucket de estado y sus versiones; eliminar solo objetos temporales propios de las sondas. La limpieza de imágenes tiene su estado separado y se coordina con T07.

## Evidencia ejecutada — 31/10/2026

Se crearon los 62 recursos Terraform de infra sin IAM nuevo. Ambas RDS quedaron disponibles, primaria en us-east-1a y standby en us-east-1b; Redis 7.1.0 informó primaria a/réplica b. Se comprobó el SG de datos sin CIDR y el esquema/índice de DynamoDB. Las EC2 definitivas de generación 2 aprobaron nuevamente bootstrap, Calico/DNS/NodePort y repetición sin recrear kind.

La sonda real aprobó las fases A seed, B lectura/escritura, A lectura y limpieza para los cinco servicios. Usó identidad de instancia LabRole y TLS SQL con certificado/hostname validados. Retiró tablas SQL, claves Redis, ítems DynamoDB, mensajes propios SQS, directorios privados de ambos hosts, archivo local de conexión y todas las versiones del objeto temporal S3. Reporte privado: `.local/t06/report.json`.

Pasaron 50 pruebas Python y seis pruebas Terraform de infra, fmt/validate y plan real final con código 0, sin cambios. Un plan adicional, nunca aplicado, cambió MySQL 8.4.11→8.4.10 y mostró únicamente actualización de RDS; ningún cambio de EC2/ALB. Se restauró la versión fijada antes del plan final. Evidencias privadas: `.local/t06/bootstrap-isolation.json`, `compute-report.json` y logs de apply/planes/SSM. La aplicación dentro de pods y el recorrido completo permanecen para T08/T11.

Referencias: [TLS RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html), [Python en AL2023](https://docs.aws.amazon.com/linux/al2023/ug/python.html), [acceso a Redis](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/accessing-elasticache.html), [SSL PostgreSQL/libpq](https://www.postgresql.org/docs/current/libpq-connect.html), [cliente PyMySQL](https://pymysql.readthedocs.io/en/latest/modules/connections.html).
