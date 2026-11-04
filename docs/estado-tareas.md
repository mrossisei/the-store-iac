# Estado de ejecución

Última revisión: 04/11/2026. Las tareas marcadas completas se publican e integran en `main` remoto; trabajo realizado en worktrees independientes para preservar los cambios del checkout original.

| Tarea | Estado | Evidencia / límites |
|---|---|---|
| T00 | Completa | Contrato, configuración compartida e inventario inicial. Ver [contrato](contrato-implementacion.md). |
| T01 | Completa | Herramientas/plugin, kind/Calico local y sonda EC2/SSM con PassRole. Restricciones de APIs y validaciones por servicio documentadas en [ejecución T01](ejecucion-t01.md). |
| T02 | Completa | Red real, estado S3, lock y convergencia comprobados; limpieza auditada. Ver [estado/red](operacion-estado-red.md). |
| T03 | Completa | Dos EC2 privadas con kind/Calico; bootstrap desde cero, NodePort/DNS/policies, repetición y reboot aprobados. Ver [cómputo](computo-t03.md). |
| T04 | Completa | Acceso SSM/TLS temporal, identidad A/B, aliases y estado independiente. Ciclo real de creación/lectura/actualización/destrucción y rechazo con un túnel caído aprobados. Ver [acceso](acceso-t04.md). |
| T05 | Completa | ALB público directo a ambas EC2:8080, listener/SG/readiness/targets contrastados en AWS. Tráfico público a ambos kind, fallo y recuperación B probados con sondas temporales; UI completa en T11. Ver [ALB](alb-t05.md). |
| T06 | Completa | RDS privadas gp2 Multi-AZ, Redis primaria/réplica en AZ distintas, DynamoDB y SQS compartidos. Escrituras/lecturas A→B→A con LabRole y TLS SQL, limpieza de sondas y convergencia real aprobadas. Ver [datos](datos-t06.md). |
| T07 | Completa | Cinco ECR inmutables, diez imágenes v1/v2 amd64 por digest, UI visible y selección v1→v2→v1 sin builds/push. Veinte pulls con LabRole desde ambos hosts definitivos. Ver [imágenes](imagenes-t07.md). |
| T08 | Completa | Veinte pods Ready, digests/IMDSv2/LabRole, compras API A↔B con producto/precios/dirección, PostgreSQL y eventos SQS, UI por cada host y ALB. Precarga y correcciones inmutables; guard de plan guardado con B caída y convergencia real aprobados. Ver [aplicación](aplicacion-t08.md). |
| T09 | Completa | Tres fases reales, 49 controles por clúster/fase, cuarentena/reversión exclusivamente diez policies y UID/restarts/templates estables. Catalog/Cart funcionales, Checkout aislado de servicios/Redis/DNS/Internet, fuentes ALB/kubelet medidas y compra restaurada A↔B/SQS. Ver [políticas](politicas-t09.md). |
| T10 | Preparada | Arnés, snapshots, sondas estrictas y flujo Cypress/orden/SQS. Bootstrap real y controles de error aprobados; app/full se ejecutan en T11/T12. Ver [verificación](verificacion-t10.md). |
| T11 | Pendiente | Integración y navegador/persistencia completos; incorpora el despliegue de T15. |
| T12 | Pendiente | Cuatro campañas reales con baseline restaurado y evidencia en ambas copias; depende de T11. |
| T13 | Pendiente | Ciclo formal destroy/recreación desde Actions y auditoría; depende de T12. |
| T14 | Pendiente | Guía, informe, presentación y ensayo; borrador en paralelo, cierre tras T13. Referencia Grupo 12 revisada y [propuesta de formato/16 láminas](referencia-presentacion-t14.md) documentada; PPT final y ensayo pendientes. |
| T15 | Planificada | Plan/Apply/Destroy manuales en GitHub Actions, secrets temporales, tres estados y acceso SSM. Se incorpora antes de T11; sin workflows implementados ni secrets configurados por esta revisión. Ver [alcance T15](automatizacion-t15.md). |

Para T04/T05 se recrearon red/EC2 y se agregó el ALB. Al terminar ambas tareas se retiraron las sondas y los 49 recursos de infra; auditoría final aprobada por IDs: EC2 terminadas, EBS/ALB/target group/listener/VPC/ENI/SG/subredes/rutas/endpoints/EIP eliminados y NAT deleted. Estados infra/app vacíos, túneles y kubeconfigs temporales retirados. Se conserva el bucket de estado/versiones y el estado local privado de bootstrap. No se declararon recursos IAM ni se modificó LabRole.

Para T06/T07 se recreó infra con datos (62 recursos Terraform, incluidos dos `random_password`). T06 terminó sus sondas y retiró datos/archivos privados y versiones temporales S3. Después se destruyó infra y la auditoría por IDs aprobó: cuatro EC2 actuales/anteriores terminadas, cuatro EBS raíz y dos EIP eliminados, dos NAT deleted, sin RDS/Redis/DynamoDB/SQS, snapshots propios ni recursos de VPC/ALB restantes. Estado infra vacío, app vacía y sin túneles/manifests temporales.

T06 se publicó en `dc4c68d`; T07 (`6423951`) se integró mediante merge `fbc462f`. Se conservan intencionalmente el bucket/versiones de estado, el estado privado de bootstrap y los cinco repositorios ECR con diez imágenes verificadas por digest para T08. La combinación aprobó 59 pruebas Python, ocho pruebas Terraform y planes reales sin cambios antes del destroy. Auditoría privada: `.local/t06/cleanup-report.json`.

T08 y T09 aprobaron las dos aplicaciones completas y la cuarentena real en ambos kind. El 4/11 se agregó T15 (operación GitHub Actions) antes de T11 (integración por navegador); siguen T12 (campañas), T13 (destroy/recreación) y T14 (entrega/ensayo). T14 puede avanzar como borrador en paralelo. Para las siguientes pruebas AWS recrear infra y esperar bootstrap; no reconstruir tags v1/v2 existentes. Un solo operador aplica al estado compartido, coordinando ejecución local y Actions. Cada tarea se publica e integra en main al cerrarse; los cambios sin commit del checkout original se preservan.

Los mocks y consultas Describe no se presentan como pruebas de creación o de funcionamiento de la aplicación completa. Los detalles, comandos reproducibles y límites están en las guías enlazadas.

T08 recuperó el bucket y los ECR tras su desaparición externa del laboratorio, conservando los diez digests originales. Publicó cuatro correcciones nuevas de Checkout/Orders en un manifest de aplicación separado. Se conservan catorce artefactos en cinco repositorios. Pasaron 75 pruebas Python, diez Terraform, dos Jest y cuatro Java; las correcciones Orders también aprobaron PostgreSQL local en ambas versiones y lectura tras reinicio. La infraestructura y la aplicación de esta ejecución ya se retiraron y auditaron; se conservan ECR y estado para T11/T12. Evidencia privada: `.local/t08/application-report.json`, `guard/report.json`, `publishers-idempotent.json` y planes de convergencia. El flujo por navegador y las campañas siguen en T11/T12.

T09 aprobó 84 pruebas Python y catorce Terraform combinadas, tres fases AWS y la compra API posterior. Los planes de cuarentena/restauración cambiaron únicamente diez NetworkPolicies por transición. La captura de fuentes confirmó túneles Calico para ALB y Node InternalIP para kubelet; no se reiniciaron pods durante la campaña. La medición es pasiva y no depende de logs Tomcat (UI usa Netty).

Cierre T08/T09 publicado en `main`: T08 `cb93862` (incluye el fix Orders `8545862`) y merge T09 `61158fa`, cuyo segundo padre es `2e42616`. Después se retiraron los 54 objetos Kubernetes y se verificó el namespace ausente en ambos kind y el estado app vacío antes de retirar hosts.

La limpieza de los 62 recursos AWS terminó y aprobó auditoría por IDs de esta generación: dos EC2 terminadas, dos EBS raíz y dos EIP ausentes, dos NAT deleted, sin VPC/ENI/SG/subredes/rutas/endpoints/ALB/listener/target group propios, ni RDS/Redis/DynamoDB/SQS, nodos Redis o snapshots propios. Estado infra vacío; sin túneles, manifests ni kubeconfigs temporales. El perfil preexistente `LabInstanceProfile` y `LabRole` siguen presentes.

Se conservan intencionalmente el bucket/versiones y los estados, el estado privado de bootstrap y cinco repositorios ECR inmutables con **catorce imágenes verificadas por digest**: diez originales y cuatro correcciones Checkout/Orders. Para T11 recrear infra, esperar bootstrap y aplicar la versión seleccionada; no reconstruir ni sobrescribir artefactos existentes. Evidencia privada: `.local/t08/{app-cleanup-report,cleanup-report,iam-retained}.json`. El checkout original conserva sus cambios del usuario sin commit; la integración se publicó desde el worktree de ejecución.
