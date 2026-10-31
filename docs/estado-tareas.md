# Estado de ejecución

Última revisión: 31/10/2026. Rama `feat/t00-t02-kind-foundations`, en un worktree independiente para preservar los cambios del checkout original.

| Tarea | Estado | Evidencia / límites |
|---|---|---|
| T00 | Completa | Contrato, configuración compartida e inventario inicial. Ver [contrato](contrato-implementacion.md). |
| T01 | Completa | Herramientas/plugin, kind/Calico local y sonda EC2/SSM con PassRole. Restricciones de APIs y validaciones por servicio documentadas en [ejecución T01](ejecucion-t01.md). |
| T02 | Completa | Red real, estado S3, lock y convergencia comprobados; limpieza auditada. Ver [estado/red](operacion-estado-red.md). |
| T03 | Completa | Dos EC2 privadas con kind/Calico; bootstrap desde cero, NodePort/DNS/policies, repetición y reboot aprobados. Ver [cómputo](computo-t03.md). |
| T10 | Preparada | Arnés, snapshots, sondas estrictas y flujo Cypress/orden/SQS. Bootstrap real y controles de error aprobados; app/full se ejecutan en T11/T12. Ver [verificación](verificacion-t10.md). |

Se retiraron los recursos AWS de las pruebas; se conserva intencionalmente el bucket de estado/versiones y el estado local privado de bootstrap. Los recursos IAM del Lab no se modificaron. Para continuar se recrea infra con apply y se espera el verificador T03.

Sigue T04: acceso del operador y providers Terraform para ambos Kubernetes. En paralelo se pueden implementar T05 (ALB), T06 (datos) y T07 (imágenes) contra los contratos. Un solo operador aplica al estado compartido.

Los mocks y consultas Describe no se presentan como pruebas de creación o de funcionamiento de la aplicación completa. Los detalles, comandos reproducibles y límites están en las guías enlazadas.
