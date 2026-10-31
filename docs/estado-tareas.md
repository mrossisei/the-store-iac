# Estado de ejecución

Última revisión: 31/10/2026. Implementación en `feat/t00-t02-kind-foundations`, iniciada desde `d7d7daa`, para preservar el checkout original con cambios locales.

| Tarea | Implementación | Evidencia / falta para cierre operativo |
|---|---|---|
| T00 | Completa | Contrato de interfaces y configuración compartida. Sesión e inventario inicial comprobados antes de crear recursos. |
| T01 | Completa | Herramientas/plugin disponibles, kind/Calico/NodePort y policies probados. Sonda EC2 con PassRole y sesión SSM real aprobada y retirada. Cuotas/precios denegados y verificaciones propias de T03–T08 documentados en ejecucion-t01.md. |
| T10 | Preparada | Arnés de ambos kind/ALB, sondas estrictas, snapshots, Cypress y correlación orden/SQS. Tests locales aprobados; ejecución completa en T11/T12. Ver verificacion-t10.md. |
| T02 | Completa | Apply real de 42 recursos, verificación AWS, bloqueo S3 y segundo plan sin cambios. Destroy y auditoría sin huérfanos; bucket/estado conservados. Ver operacion-estado-red.md. |

No se interpreta una validación estática o un mock como evidencia de que el Lab habilita un recurso.

La siguiente implementación es T03 (dos EC2 privadas con kind). T05/T06/T07 pueden programarse contra el contrato; T06 y T07 ya tienen la base de red/estado verificada. Para desplegar, recrear infra siguiendo operacion-estado-red.md.
