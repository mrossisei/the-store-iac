# Qué aporta la clase de IaC y Terraform a la presentación

Fuente revisada: **10-IaC_Terraform.pptx (1).pdf**, 33 páginas, materia **82.08 Cloud Computing**, adjuntada por el usuario. La presentación del Grupo 2 sigue perteneciendo a **72.20 Redes de Información**; la preentrega vigente conserva la autoridad sobre integrantes, legajos y alcance del POC.

## Ideas que se incorporan

- **Escala empresarial, p. 2–3.** El problema es mantener y cambiar una infraestructura que crece. La clase menciona Despegar como una pregunta para discutir esa escala; no presenta su implementación ni resultados medidos. La exposición usa situaciones comprensibles de una tienda online.
- **Idempotencia, p. 6.** Volver a aplicar la misma definición busca mantener el mismo estado esperado. Se explica como poder repetir el procedimiento sin volver a crear todo, conservando el estado y comprobando desvíos con un nuevo plan.
- **Siete ventajas de IaC, p. 7–8.** Automatización y velocidad; consistencia y estandarización; versiones; costos; escalabilidad y reutilización; seguridad; documentación viva. Se mantienen tres bloques de beneficios con ejemplos del proyecto.
- **Más que recursos de nube, p. 14.** Terraform puede administrar diferentes ámbitos mediante proveedores. La lámina presenta nube, equipos propios y servicios externos como ámbitos del producto. El POC usa AWS y Kubernetes.
- **Trabajo compartido, p. 19–21.** El estado remoto aporta un registro común y puede usar bloqueo, cifrado y controles de acceso. Se traduce como coordinar al equipo y evitar escrituras simultáneas cuando el backend y su configuración lo soportan.
- **Un modelo para varios entornos, p. 24–25 y 31–32.** Variables y módulos permiten adaptar una definición común. Se convierte en el ejemplo empresarial de abrir un espacio de pruebas separado y retirarlo al finalizar. Las dos copias del POC comparten datos y sirven la misma tienda; no son pruebas y producción separadas.
- **Cambios con protecciones, p. 4 y 30.** La posibilidad de preparar un reemplazo antes de retirar el recurso anterior y de rechazar la destrucción de recursos protegidos se explica mediante decisiones operativas. Son capacidades del producto, sin afirmar que estos ejemplos sean nuevas pruebas de la implementación.

## Cómo se explica a una audiencia no técnica

El recorrido principal habla de modelos reutilizables, reglas de acceso, recursos, cambios, pruebas y operación. La arquitectura muestra entrada común, dos copias de la tienda y datos compartidos. Los nombres de servicios AWS, direcciones IP, archivos de configuración y sintaxis quedan en notas y anexos. Los nombres breves de operaciones `init`, `plan`, `apply` y `destroy` se conservan junto con su significado para conectar con la pantalla compartida.

Los ejemplos empresariales ilustran adopción; no agregan casos a la demo. La demo mantiene su único separador y sus cuatro casos en el guion del operador. La lámina de IA continúa opcional y oculta.

## Precisiones que se conservan al adaptar el material

Terraform puede actualizar recursos existentes o reemplazarlos, según el recurso y el cambio. El enfoque inmutable es una decisión de diseño. `create_before_destroy` ordena crear antes de retirar, pero no garantiza por sí solo continuidad de la aplicación. `prevent_destroy` depende de que la regla siga en la configuración y no sustituye backups.

IaC ayuda a controlar diferencias y errores; una definición escrita no los elimina automáticamente. Git permite recuperar una configuración previa, que todavía debe revisarse antes de aplicar. No equivale a restaurar datos. El proyecto utiliza bloqueo nativo del backend S3, no necesita adoptar el ejemplo de bloqueo con DynamoDB de la clase. No se incorporan afirmaciones sobre licencias que no sean necesarias para el objetivo de la charla.

Se mantienen las ventajas de costos como posibilidades de uso eficiente y retiro de entornos temporales, sin porcentajes de ahorro ni tiempos de despliegue inventados.

Referencias de precisión: [ciclo de vida](https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle), [backend S3](https://developer.hashicorp.com/terraform/language/backend/s3), [módulos](https://developer.hashicorp.com/terraform/language/modules).
