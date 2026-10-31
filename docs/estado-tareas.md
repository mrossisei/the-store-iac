# Estado de ejecución

Última revisión: 31/10/2026. Rama `feat/t00-t02-kind-foundations`, en un worktree independiente para preservar los cambios del checkout original.

| Tarea | Estado | Evidencia / límites |
|---|---|---|
| T00 | Completa | Contrato, configuración compartida e inventario inicial. Ver [contrato](contrato-implementacion.md). |
| T01 | Completa | Herramientas/plugin, kind/Calico local y sonda EC2/SSM con PassRole. Restricciones de APIs y validaciones por servicio documentadas en [ejecución T01](ejecucion-t01.md). |
| T02 | Completa | Red real, estado S3, lock y convergencia comprobados; limpieza auditada. Ver [estado/red](operacion-estado-red.md). |
| T03 | Completa | Dos EC2 privadas con kind/Calico; bootstrap desde cero, NodePort/DNS/policies, repetición y reboot aprobados. Ver [cómputo](computo-t03.md). |
| T04 | Completa | Acceso SSM/TLS temporal, identidad A/B, aliases y estado independiente. Ciclo real de creación/lectura/actualización/destrucción y rechazo con un túnel caído aprobados. Ver [acceso](acceso-t04.md). |
| T05 | Completa | ALB público directo a ambas EC2:8080, listener/SG/readiness/targets contrastados en AWS. Tráfico público a ambos kind, fallo y recuperación B probados con sondas temporales; UI completa en T11. Ver [ALB](alb-t05.md). |
| T10 | Preparada | Arnés, snapshots, sondas estrictas y flujo Cypress/orden/SQS. Bootstrap real y controles de error aprobados; app/full se ejecutan en T11/T12. Ver [verificación](verificacion-t10.md). |

Para T04/T05 se recrearon red/EC2 y se agregó el ALB. Al terminar ambas tareas se retiraron las sondas y los 49 recursos de infra; auditoría final aprobada por IDs: EC2 terminadas, EBS/ALB/target group/listener/VPC/ENI/SG/subredes/rutas/endpoints/EIP eliminados y NAT deleted. Estados infra/app vacíos, túneles y kubeconfigs temporales retirados. Se conserva el bucket de estado/versiones y el estado local privado de bootstrap. No se declararon recursos IAM ni se modificó LabRole.

Siguen T06 (datos) y T07 (imágenes), que pueden implementarse en paralelo contra los contratos; T08 depende además de esas tareas. Para volver a probar AWS, recrear infra y esperar bootstrap T03. Un solo operador aplica al estado compartido. Cada tarea se publica e integra en main al cerrarse; los cambios sin commit del checkout original se preservan.

Los mocks y consultas Describe no se presentan como pruebas de creación o de funcionamiento de la aplicación completa. Los detalles, comandos reproducibles y límites están en las guías enlazadas.
