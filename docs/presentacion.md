# Presentación final — The Store con Terraform

Versión editorial clara del 04/11/2026, adaptada para una audiencia no técnica. Presenta Terraform mediante situaciones de negocio y beneficios concretos. Conserva los datos y el alcance del Grupo 2 de la preentrega vigente EC2 + kind.

- [PPTX editable con notas](entrega/presentacion.pptx)
- [PDF de la presentación](entrega/presentacion.pdf)
- [Guion del orador y del operador](entrega/guion-presentacion.md)
- [Anexos técnicos en PDF](entrega/anexos.pdf)
- [Qué se tomó de la clase de Terraform](referencia-clase-terraform.md)

## Recorrido

1. Carátula.
2. Las piezas que necesita una compra.
3. El riesgo de gestionar cambios sin un proceso común.
4. Terraform como propuesta para crear, cambiar y retirar con control.
5. Una definición escrita para crear y actualizar recursos.
6. Automatizar y repetir el mismo estándar.
7. Conservar historial, revisar accesos y mantener una definición actualizada.
8. Retirar recursos temporales y reutilizar un modelo.
9. Ejemplo empresarial: probar cambios en un espacio separado.
10. Ejemplo empresarial: preparar reemplazos y proteger recursos críticos.
11. Usar el mismo proceso para distintos servicios y proveedores.
12. Revisar el impacto antes de hacer cambios.
13. Compartir un registro y ordenar las tareas.
14. Arquitectura simplificada: entrada común, dos copias de la tienda y datos compartidos.
15. Demo: único separador para compartir pantalla.
16. Cierre de la propuesta de adopción.
17. Preguntas.

El lenguaje del recorrido principal evita sintaxis, direcciones IP y listas de productos AWS. Los términos técnicos de la clase quedan explicados en las notas y los anexos. Las siete ventajas de IaC y cinco características de Terraform se expresan mediante sus efectos para el equipo y el negocio.

Los ejemplos empresariales derivan de variables, módulos y reglas de ciclo de vida de la clase **82.08 Cloud Computing**. Ilustran capacidades de Terraform; no se atribuyen al POC ambientes separados de pruebas y producción, una transición sin interrupciones ni resultados medidos que no se hayan comprobado. La materia y los integrantes de nuestra carátula siguen siendo los de **72.20 Redes de Información**.

Los cuatro casos de la demo quedan en el guion del operador, sin diapositivas individuales. **Slide de uso de IA** es opcional y está oculta antes de la demo. Hay seis anexos técnicos ocultos, accesibles desde Preguntas, que no se incluyen en el PDF principal.

## Tiempo y alcance

Objetivo: 24 minutos de contenido, 1 de transiciones y 5 de preguntas. Contexto y propuesta: 2 min 10 s; Terraform, beneficios, ejemplos y arquitectura: 10 min 5 s; demo: 11 minutos; cierre: 45 segundos. Ensayar y medir los casos antes de exponer.

La generación solo produce documentos: no ejecuta pruebas ni opera AWS. La implementación usa dos EC2 privadas, cada una con un kind independiente, y ALB. La versión simplificada actual se opera desde una sola configuración en `terraform/`, con un estado remoto S3; el guion usa los comandos y kubeconfigs de esa versión.

Fuente editable: [generador](../scripts/generar-presentacion.py). Los textos y diagramas de la PPT son objetos editables.
