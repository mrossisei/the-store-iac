# T14 — Referencia de formato y propuesta de presentación

Revisión del 4/11/2026 de `Presentacion-Kubernetes-Grupo12.pptx`, recibido en el directorio `redes/`, fuera del repositorio. SHA-256: `0b4248266d9c9f9d257efab9125fce2643a39a237e9005079b726a193e46ce31`.

Se extrajo el texto de las 21 diapositivas y se convirtió una copia a PDF para inspeccionar su diseño. Se revisaron visualmente portada, arquitectura, recorrido HTTP y conclusiones (1, 8, 13 y 20). La conversión y las imágenes quedan como material local de consulta; el archivo original permanece intacto. Esta revisión no certifica las implementaciones ni las pruebas que afirma el grupo anterior.

Esta referencia se incorpora a **T14**, sin crear otra tarea. Es una guía para preparar el PPT; T14 sigue pendiente y todavía no se generó nuestra presentación final.

## Cómo está organizada la referencia

| Diapositivas | Bloque | Recurso de exposición |
|---|---|---|
| 1–2 | Portada y agenda | Tema, integrantes y recorrido de la charla. |
| 3–6 | Problemática | The Store, contenedores, orquestación y dificultad de montar un clúster. |
| 7–8 | Solución y arquitectura | Tres casos de uso y topología mediante bloques. |
| 9–13 | Tecnologías y red | Resumen del stack, una lámina por herramienta, flujo HTTP y tabla de redes/puertos. |
| 14–16 | Operación y validación | Secuencia de despliegue, compra E2E y ampliación con un worker. |
| 17 | Demo | Separador de pantalla para pasar a la demostración. |
| 18–21 | Cierre | Alternativas, límites, aprendizajes y preguntas. |

El reparto está identificado como Orador 1/2/3. El primero introduce el problema y vuelve al cierre; el segundo desarrolla solución/tecnologías; el tercero explica operación/validación antes de la demo. Los nombres siguen como placeholders en el archivo recibido.

## Formato visual que conviene tomar

- **Lienzo 16:9.** Portada y conclusiones con franja azul vertical; láminas de contenido con una línea azul arriba, sección, título, línea divisoria y pie numerado.
- **Paleta consistente:** azul `#326CE5`, texto oscuro `#1A2332`, gris de apoyo `#4A5568`, fondos blancos y paneles gris claro. Colores de alerta solo en límites o advertencias puntuales.
- **Jerarquía:** una idea principal por lámina, títulos grandes y subtítulos cortos. Calibri para texto y Consolas para comandos/direcciones. Es un formato fácil de recrear con objetos editables.
- **Diagramas simples:** tarjetas para componentes y flechas para el recorrido de red; tabla breve para CIDR/puertos. La arquitectura (8) y el camino host→pod (13) son las referencias más útiles.
- **Código en su contexto:** pequeños extractos junto a una explicación de qué hacen. Los comandos largos se pueden dejar en notas o en el how-to.
- **Transición a demo y cierre explícito:** una pantalla anuncia la demo; luego se vuelve a límites y resultados.

La referencia tiene bastante texto y numerosos tamaños de 9–16 pt. Para pantalla compartida conviene reducirlo: cuerpo de aproximadamente 20–24 pt, títulos de 30–36 pt, 3–5 puntos por lámina y etiquetas de diagramas legibles. Comprobarlo al tamaño real de la videollamada, sin depender del zoom del editor. Son objetivos de diseño para nuestro PPT, no especificaciones del archivo recibido.

## Adaptación al proyecto vigente

El grupo anterior presenta Vagrant + Ansible + K3s, una red local con Flannel/ingress-nginx y el alta de un worker. Nuestra historia debe seguir la preentrega vigente y la implementación de este repo:

- **Objetivo:** infraestructura reproducible en AWS con Terraform y The Store distribuida en dos copias.
- **Arquitectura:** dos EC2 privadas, una por AZ, cada una con su propio kind (control plane + worker). Son dos clústeres independientes; no se reprograman pods de una EC2 a la otra.
- **Red:** VPC `10.0.0.0/16`, seis subredes /24; pods `10.244.0.0/16` y Services `172.20.0.0/16` internos de cada kind. Datos administrados compartidos por ambas copias.
- **HTTP:** navegador → ALB:80 → EC2:8080 → mapeo kind:30080 → NodePort UI → pod:8080. Para administrar, mostrar aparte operador/runner → SSM → API de cada kind con TLS.
- **Terraform:** tres estados remotos (infra, imágenes, aplicación), bootstrap separado, bloqueo y orden de operación. No usar la raíz histórica EKS.
- **Artefactos:** versiones v1/v2 existentes por digest en ECR, precarga con LabRole; cambios de versión sin build ni push durante la demo.
- **Políticas:** cuarentena por cambios de NetworkPolicies, sin modificar PodTemplate ni reiniciar Checkout. Evidencia funcional además del conteo de objetos.
- **Escala:** UI 2→4→2 por kind; 20→24→20 pods app totales y siempre dos EC2. El caso no agrega nodos ni capacidad física.
- **Acciones:** presentar Plan/Apply/Destroy de T15 cuando estén implementadas y probadas. Hoy están planificadas; no mostrar esa automatización como terminada.

No heredar del cierre del grupo anterior que la persistencia sea solo en memoria, que el despliegue no use cloud o que kind no sea Kubernetes real. Nuestro POC usa API Kubernetes real con nodos en contenedores y servicios de datos AWS; sus límites de disponibilidad y capacidad deben explicarse con precisión.

## Borrador propuesto: 16 diapositivas y demo integrada

| Nº | Lámina | Qué debe quedar claro |
|---|---|---|
| 1 | Portada | Tema de nuestro TP, integrantes y alcance actual. |
| 2 | Problema y The Store | Qué resuelve IaC y qué hacen los cinco microservicios. |
| 3 | Objetivos y cuatro casos | Drift AWS, escala UI, versiones y cuarentena. |
| 4 | Arquitectura AWS | Dos AZ, red, EC2/kind, ALB y datos compartidos. |
| 5 | Dentro de cada EC2 | Dos kind independientes, dos nodos internos por kind, réplicas y límites. |
| 6 | Camino de una compra | HTTP de entrada, servicios internos y persistencias. |
| 7 | Seguridad y acceso | SG, SSM/TLS, LabRole/IMDSv2 y policies; distinguir red AWS de red de pods. |
| 8 | Terraform y estados | Módulos, tres estados, plan y orden app→infra al destruir. |
| 9 | Operación con Actions | Tres workflows, ejecución serial y renovación privada del Lab, sujeto al cierre de T15. |
| 10 | Cómo validamos | Ambas copias y ALB, compra/orden/SQS, persistencia, UID y convergencia; solo evidencia realmente obtenida. |
| 11 | Demo 1: drift | Cambio AWS permitido → Plan detecta → Apply corrige. |
| 12 | Demo 2: réplicas | UI 2→4→2 en ambos kind; conteos antes/después y dos EC2 constantes. |
| 13 | Demo 3: versión | v1→v2→v1 con digests existentes, UI respondiendo y rollback comprobado. |
| 14 | Demo 4: cuarentena | Checkout aislado, catálogo/carrito funcionan, UID estables y compra tras restaurar. |
| 15 | Resultados y límites | Qué se probó, recreación/limpieza auditada y límites reales del POC. |
| 16 | Repo y preguntas | Enlaces reales al código/how-to y cierre. |

Si una lámina no cabe con texto legible, mover detalle al anexo o al how-to. La cantidad es una propuesta, no una nueva condición de entrega. Llevar capturas/video por caso y una lámina de respaldo para la demo; mantener las pruebas y sus resultados identificables por versión/commit.

**Presupuesto de exposición:** 10–12 min para contexto/arquitectura/operación, 9–11 min para los cuatro casos y 2–3 min de cierre: 21–26 min, dejando margen de transición para mantenerse debajo de 30 min. Medirlo en ensayo. No esperar un apply/destroy completo de RDS/NAT en vivo: usar el entorno ya preparado y la evidencia de ejecución/auditoría del ciclo reproducible. El tiempo de los workflows también debe medirse antes de fijar el guion.

Repartir los bloques entre A/B/C de acuerdo con el [plan](plan-de-trabajo.md), con participación de los tres y transiciones ensayadas. Mantener a una sola persona operando la infraestructura compartida, aunque cambie el orador. La revisión final y el ensayo siguen siendo trabajo pendiente de T14.

## Material que debe llegar a T14

- T11: compras por navegador, persistencia tras recreación de pods y planes convergentes. Las compras API de T08/T09 no sustituyen la evidencia de navegador.
- T12: secuencias antes/durante/después de los cuatro casos, en ambos kind y por ALB cuando corresponda.
- T13: destroy/recreación y auditoría de recursos retirados y conservados.
- T15: ejecuciones reales de Plan/Apply/Destroy, URL pública y resúmenes sanitizados. Nunca capturas con claves, tokens, contraseñas, kubeconfigs o planes sensibles.
- T14: nombres definitivos, enlaces, PPT editable, PDF exportado, respaldo de demo y ensayo completo menor a 30 min.

El archivo [presentacion.md](presentacion.md) conserva el guion histórico de EKS, que quedó desactualizado. Para crear la presentación usar esta referencia, la [preentrega vigente](preentrega-vigente.pdf), el [contrato](contrato-implementacion.md) y el [estado de ejecución](estado-tareas.md).
