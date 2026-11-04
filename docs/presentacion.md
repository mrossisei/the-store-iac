# Guion vigente — The Store en AWS con Terraform y kind

Borrador T14 del 04/11/2026. Presentación [editable](entrega/presentacion.pptx) y [PDF](entrega/presentacion.pdf). Integrantes: Matías, Juan Pablo y Federico. Referencias: [contrato](contrato-implementacion.md), [estado de tareas](estado-tareas.md) y [formato](referencia-presentacion-t14.md). El equipo que ejecuta las pruebas debe actualizar resultados y cierre con evidencia nueva antes de exponer.

## Reparto y tiempo previsto

| Láminas | Orador propuesto | Tiempo |
|---|---|---:|
| 1–3 | Matías | 3 min |
| 4–8 | Juan Pablo | 7 min |
| 9–10 | Federico | 2 min |
| 11–14 | Federico, con un solo operador | 10 min |
| 15–16 | Matías | 3 min |

Total previsto: **25 minutos**, más transiciones, inferior a 30. Es una estimación: falta medir el ensayo completo. El entorno debe estar preparado; no esperar la creación o destrucción completa de datos y red durante la exposición.

## Guion por lámina

1. Presentar objetivo e integrantes: una tienda reproducible en AWS, con dos copias.
2. Explicar el problema de cambios manuales y los cinco servicios de The Store.
3. Anunciar drift, réplicas, versiones y cuarentena como los cuatro casos de la demo.
4. Recorrer la VPC, ALB público, dos AZ con una EC2 privada cada una y los datos compartidos.
5. Cada EC2 ejecuta su propio kind con control plane y worker. Son clústeres independientes: no hay traslado de pods entre ellos y comparten recursos del host.
6. Seguir navegador → ALB:80 → EC2:8080 → kind/NodePort:30080 → UI:8080; los servicios acceden a las persistencias compartidas.
7. Separar controles de red AWS y NetworkPolicies de pods. El operador accede mediante SSM y TLS; se usa LabRole existente con IMDSv2.
8. Explicar bootstrap separado y los tres estados S3 con bloqueo. Tras revisar plan, aplicar infra antes de app; destruir app con acceso activo antes de infra.
9. Una persona opera la sesión compartida; el ciclo formal corresponde a T13.
10. T00–T09 tienen pruebas documentadas; T08 demostró compras por API y T09 políticas y restauración. T11/T12 están en prueba por el equipo; sus resultados nuevos aún no están incorporados aquí.
11. **Drift:** mostrar baseline, cambio AWS permitido, plan que lo detecta, corrección y convergencia. Enseñar evidencia antes/después de T12 cuando esté disponible.
12. **Escala:** cambiar UI de 2 a 4 y volver a 2 por kind; mostrar 20→24→20 pods totales, ambas copias y dos EC2 constantes. No afirmar que se agregaron nodos físicos.
13. **Versión:** seleccionar v1→v2→v1 por digest existente, mostrar respuesta de UI y rollback en ambas copias; no compilar ni publicar durante la demo.
14. **Cuarentena:** revisar plan de NetworkPolicies, aislar Checkout, verificar catálogo/carrito y UID estables, restaurar y comprobar compra. T09 probó el mecanismo; la campaña T12 sigue pendiente de evidencia final.
15. Distinguir lo probado de lo pendiente. Dos clústeres comparten datos pero no capacidad; el POC no demuestra por sí solo disponibilidad ni seguridad de producción.
16. Indicar repositorio, contrato, estado y guion; abrir preguntas.

## Preparación, respaldo y cierre

- Coordinar una única sesión AWS y un único operador; verificar acceso, identidad de ambas copias, baseline y URL antes de presentar. Seguir las guías actuales de T04, T08 y T10, sin usar la raíz histórica EKS.
- Obtener y registrar evidencias de navegador y persistencia T11, y antes/durante/después de los cuatro casos T12 en ambas copias y por ALB cuando corresponda. Vincularlas a versión/commit y sanitizarlas.
- Preparar capturas o video por caso como respaldo; no mostrar credenciales, kubeconfigs, contraseñas ni planes sensibles.
- Completar T13: ciclo formal de destrucción/recreación y auditoría de recursos retirados y conservados.
- Actualizar las láminas y este guion con la evidencia aceptada, ensayar con cronómetro y confirmar el reparto. El cierre y la limpieza corresponden al equipo coordinador.
