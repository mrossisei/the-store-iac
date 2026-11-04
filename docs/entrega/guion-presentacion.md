# Presentación — The Store con Terraform

PPT editorial clara, 16:9. Grupo 2 · 72.20 Redes de Información · ITBA · 2C 2026.

- Matias Rossi — 63202
- Juan Pablo Birsa — 64500
- Federico Viera — 62022

## Archivos y uso

- `presentacion.pptx`: texto y diagramas editables, con notas del orador.
- `presentacion.pdf`: las 17 láminas del recorrido principal.
- `anexos.pdf`: seis láminas técnicas de respaldo, separadas del recorrido.
- `guion-presentacion.md`: este guion y la preparación de la demo.
- `estructura.json`: contenido de notas, tiempos e índices para regeneración.

La lámina **Slide de uso de IA** está oculta antes de la demo. Los anexos también están ocultos; se accede a ellos desde el vínculo de la lámina Preguntas. Para usar IA, completar solo con usos reales del grupo y habilitar esa lámina desde PowerPoint/Impress. El PDF principal no incluye las láminas ocultas.

## Tiempo y reparto propuesto

Contenido: **24 min**. Reservar **1 min** para transiciones y **5 min** para preguntas. Si se habilita IA, usar hasta 30 s del margen. El tiempo de demo es una estimación a medir en ensayo; no presupone que las operaciones AWS ya fueron cronometradas.

- Matias: contexto y propuesta; vuelve al cierre.
- Juan Pablo: Terraform, beneficios, ejemplos de adopción y arquitectura.
- Federico: demo. Una sola persona opera la sesión.

El reparto es una propuesta editable. Los tres deben poder explicar la implementación completa.

## Guion por diapositiva

### 1. Infraestructura como código con Terraform

**Orador:** Matias. **Tiempo objetivo:** 20 s.

Somos el Grupo 2. Vamos a mostrar cómo Terraform nos ayuda a crear y cambiar los recursos que necesita The Store. El objetivo es que operar la tienda sea más repetible, revisable y menos dependiente de tareas manuales.

**Transición:** Para entender por qué esto importa, primero veamos qué necesita una compra.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

Presentar al grupo y el tema. Nuestro trabajo toma The Store, una tienda online de cinco microservicios, y usa Terraform para administrar la infraestructura que la sostiene en AWS. La pregunta que organiza la charla es cómo repetir un entorno y hacer cambios con control. Vamos a mostrar el problema, la propuesta y la herramienta; después haremos cuatro cambios sobre la tienda en vivo. No prometer cifras de ahorro ni disponibilidad que no hayamos medido.

</details>

**Fuentes:**

- Pre Entrega - Grupo 2 -1.pdf · carátula y secciones 1–3

### 2. Una compra depende de varias piezas

**Orador:** Matias. **Tiempo objetivo:** 20 s.

El cliente ve una tienda: busca productos, arma un carrito y compra. Para que eso funcione hay varias piezas trabajando juntas. Nuestro proyecto se ocupa de los recursos que las sostienen y de cómo administrarlos cuando necesitamos hacer cambios.

**Transición:** El desafío no termina cuando conseguimos que la tienda arranque.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

The Store permite recorrer un catálogo, armar un carrito y confirmar una compra. La UI es la cara visible. Por detrás colaboran Catalog, Cart, Checkout y Orders. Separar estas responsabilidades permite cambiar cada servicio, pero también exige coordinar conexiones, despliegues y datos. En el punto de partida, un script arma el entorno local y los servicios usan almacenamiento en memoria. Nuestra propuesta lleva la operación a AWS y conecta persistencias administradas. No hace falta describir los lenguajes ni los puertos para entender la necesidad de administrar el conjunto.

</details>

**Fuentes:**

- Preentrega vigente · secciones 1–2

### 3. Una tienda online necesita cambios bajo control

**Orador:** Matias. **Tiempo objetivo:** 45 s.

Poner la tienda en marcha es solo el comienzo. Después aparecen nuevas necesidades: preparar una prueba, publicar una mejora o responder a un problema. Si cada cambio depende de reconstruir pasos y recordar decisiones, el equipo pierde tiempo y aumenta el riesgo de equivocarse. Una configuración inesperada puede terminar afectando una compra. Necesitamos una forma compartida de saber qué tenemos y cómo cambiarlo.

**Transición:** Nuestra solución comienza por cambiar la forma de definir y modificar ese entorno.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

No partimos de una aplicación que nadie puede ejecutar: ya existe local.sh. Ese script automatiza pasos para crear kind, construir imágenes y aplicar objetos. El problema es que esa secuencia no describe de manera unificada el resultado esperado ni mantiene el inventario y el plan de cambios que necesitamos para gestionar la infraestructura. Al crecer el entorno, reproducirlo y modificarlo exige más coordinación. Una configuración cambiada desde la consola puede quedar fuera de lo acordado. Y ante un incidente hay que reconstruir qué existe y qué debería existir antes de decidir cómo actuar. Desde la perspectiva de quien financia el proyecto, esto significa tiempo operativo, incertidumbre y exposición a errores. Son riesgos del enfoque, no estadísticas de incidentes que hayamos medido en la tienda. La inversión que proponemos apunta a que el conocimiento del entorno quede escrito y a que los cambios sean revisables por el equipo.

</details>

**Fuentes:**

- Preentrega vigente · sección 1

### 4. Terraform para crear, cambiar y retirar con control

**Orador:** Matias. **Tiempo objetivo:** 45 s.

La propuesta es dejar escrita la definición del entorno y usar un proceso común para administrarlo. Antes de cambiar algo, vemos qué va a pasar. Después decidimos si aplicarlo y comprobamos el resultado. Esa definición queda disponible para el equipo, con historial de modificaciones. Terraform es la herramienta que conecta lo que necesitamos con los recursos de la tienda y organiza las acciones para crearlos, cambiarlos o retirarlos.

**Transición:** La herramienta que elegimos para hacerlo es Terraform.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

Proponemos administrar el entorno como una configuración versionada. El equipo define qué necesita la tienda: red, cómputo, balanceador, datos y despliegues. Esa definición puede revisarse en Git y usarse para recrear recursos. Antes de tocar el entorno se calcula una propuesta de cambios. Después se aplica y se comprueba el resultado. El estado vincula la configuración con los recursos que administra la herramienta. La solución concreta de nuestro grupo usa Terraform en AWS y administra también los objetos de los dos clústeres kind. Esto no elimina la necesidad de probar ni decide por nosotros si una modificación conviene. Nos da una base común para entender y ejecutar los cambios. El valor es que otra persona del equipo pueda revisar y repetir el procedimiento.

</details>

**Fuentes:**

- Preentrega vigente · secciones 1–3
- https://developer.hashicorp.com/terraform/intro

### 5. Terraform crea y actualiza los recursos de la tienda

**Orador:** Juan Pablo. **Tiempo objetivo:** 45 s.

Terraform toma una definición escrita de los recursos que necesitamos y calcula cómo llevarla a la práctica. Por ejemplo, la tienda requiere conectividad, servidores y servicios para guardar sus datos. En lugar de configurar cada pieza por separado, podemos administrar el conjunto con la misma herramienta. Nosotros seguimos decidiendo qué necesita la tienda y revisando los cambios; Terraform se encarga de organizar y ejecutar esas acciones.

**Transición:** Primero veamos qué gana el equipo al adoptar este enfoque.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

Terraform es una herramienta de infraestructura como código de HashiCorp. Definimos recursos en archivos legibles, en un lenguaje declarativo llamado HCL. Declarativo significa expresar el resultado deseado, por ejemplo una red y dos máquinas, en lugar de escribir cada clic que haríamos en una consola. Terraform se comunica con las APIs mediante providers. En este proyecto utilizamos AWS para la infraestructura y Kubernetes para objetos de aplicación. Los módulos agrupan recursos relacionados. La herramienta calcula dependencias y acciones; el equipo sigue siendo responsable de elegir la arquitectura, revisar el plan y validar el funcionamiento. Docker y kind se preparan mediante el bootstrap automatizado de las EC2. Terraform administra esos recursos y su configuración; no reemplaza toda tarea operativa.

</details>

**Fuentes:**

- https://developer.hashicorp.com/terraform/intro
- README y terraform/main.tf · configuración actual

### 6. Crear más rápido y repetir el mismo estándar

**Orador:** Juan Pablo. **Tiempo objetivo:** 65 s.

La primera ventaja es automatizar el trabajo repetitivo. Una definición puede coordinar la creación de varios recursos, sin configurar cada uno a mano. La segunda es repetir un estándar: las copias del entorno parten de reglas conocidas, con diferencias que elegimos de forma explícita. En The Store usamos la misma definición de aplicación para las dos copias de la tienda. Además, repetir el procedimiento busca mantener lo que definimos, sin volver a crear todo. Para una empresa esto significa menos tareas manuales y menos dependencia de cómo las recuerda cada persona.

**Transición:** Además de ejecutar, necesitamos saber qué se cambia y poder revisar sus reglas.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

Estas son dos razones para adoptar infraestructura como código. Automatización y velocidad: una configuración permite crear recursos relacionados sin configurar cada uno a mano. En The Store esto abarca VPC, subredes, EC2, balanceador y datos. Terraform resuelve sus operaciones y podemos repetir el procedimiento. La velocidad proviene de reducir tareas manuales; no mostramos un tiempo de creación que no hayamos medido. Consistencia y estandarización: el mismo módulo de aplicación se utiliza en los dos kind, con parámetros conocidos. También podemos reutilizar definiciones entre entornos, reduciendo diferencias como un Security Group inesperado en testing. Es una capacidad de adopción, no la afirmación de que el POC tenga ambientes de testing y producción. La clase agrega idempotencia: con el estado conservado y sin desvíos, repetir la misma definición busca mantener el mismo resultado, sin duplicar recursos. Para la organización, el beneficio es menos trabajo repetitivo y una base común para operar.

</details>

**Fuentes:**

- Clase 82.08 Cloud Computing · pp. 7–8 · ventajas IaC 1 y 2
- terraform/main.tf · app_a y app_b

### 7. Cada cambio se puede revisar, auditar y entender

**Orador:** Juan Pablo. **Tiempo objetivo:** 65 s.

Los cambios quedan guardados con historial: podemos ver qué se modificó, quién lo hizo y qué versión se revisó. Las reglas de acceso también quedan escritas, de modo que el equipo puede examinarlas antes de aplicarlas. Y la definición funciona como una documentación que acompaña a la operación: describe cómo debería estar armado el entorno. Así podemos responder preguntas concretas sobre la tienda sin depender únicamente de la memoria de alguien o de un documento separado que quedó viejo.

**Transición:** El valor también se refleja en cómo usamos los recursos y reutilizamos las configuraciones.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

Control de versiones: al guardar la configuración en Git tenemos historial de cambios, autores y revisiones. Podemos recuperar una definición anterior y evaluar su plan antes de aplicarla. Git aporta esa trazabilidad; Terraform ejecuta el cambio. Mejora en la seguridad: las reglas de acceso y las políticas quedan escritas. En The Store se ven en Security Groups y NetworkPolicies. Eso permite revisión por pares y análisis con herramientas automáticas; no atribuimos a Terraform un escáner incorporado ni afirmamos que este POC ya tenga ese análisis automatizado. Documentación viva: el código expresa el estado esperado del entorno y se modifica junto con el cambio, reduciendo la dependencia de un documento separado. El entorno real se contrasta con plan. Recuperar una configuración anterior exige revisar sus efectos; el historial de Git no es un respaldo de las bases.

</details>

**Fuentes:**

- Clase 82.08 Cloud Computing · pp. 7–8 · ventajas IaC 3, 6 y 7
- Guía de políticas del proyecto

### 8. Entornos temporales, soluciones reutilizables

**Orador:** Juan Pablo. **Tiempo objetivo:** 65 s.

Poder crear y retirar un entorno con un proceso repetible permite usar recursos durante el tiempo en que hacen falta. Un espacio temporal de pruebas puede eliminarse al terminar, ayudando a evitar gasto ocioso. También podemos reutilizar un modelo y adaptarlo a otra necesidad, cambiando su tamaño o ubicación sin volver a definir cada componente. El valor está en aprovechar trabajo ya realizado. En nuestro laboratorio los recursos consumen presupuesto, por eso su retiro también forma parte del procedimiento. El ahorro concreto depende de cómo se utilicen y de qué recursos se conserven.

**Transición:** Por ejemplo, una empresa puede abrir un espacio de pruebas desde un modelo común.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

Crear y retirar entornos temporales ayuda a evitar gasto ocioso. El proyecto opera con una sola configuración y un backend S3. Revisar destroy y auditar después: se retiran los recursos gestionados, incluidos datos según el plan; el bucket y los roles preexistentes se conservan fuera de esta configuración. Los módulos encapsulan configuraciones y parámetros; aplicación se utiliza dos veces, una por kind. UI 2→4 no agrega EC2 ni CPU/memoria física. El ahorro real depende de recursos, uso y duración.

</details>

**Fuentes:**

- Clase 82.08 Cloud Computing · pp. 7–8 · ventajas IaC 4 y 5
- https://developer.hashicorp.com/terraform/language/modules
- README vigente · ciclo de vida del entorno

### 9. Probar cambios sin tocar la tienda en operación

**Orador:** Juan Pablo. **Tiempo objetivo:** 60 s.

Pensemos en una empresa que quiere probar una mejora sin tocar la tienda que atiende clientes. Puede preparar un espacio separado a partir de un modelo común, adaptarlo para esa prueba y retirarlo cuando termina. Eso permite repetir una configuración conocida y evitar que cada equipo empiece desde cero. Es un ejemplo de adopción de Terraform tomado de las posibilidades que explica la clase. Nuestro proyecto reutiliza definiciones para dos copias de la tienda; crear ambientes separados de pruebas y operación sería una aplicación adicional.

**Transición:** Otra situación es cambiar un recurso importante con un orden y unas protecciones definidos.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

Ejemplo de adopción empresarial derivado de la clase: antes de lanzar un cambio necesitamos probarlo sin afectar la tienda que atiende clientes. Un modelo reutilizable permite preparar un espacio separado y adaptar sus nombres, tamaños y ubicación mediante parámetros. Al terminar, retiramos los recursos temporales. El valor combina repetibilidad, menos trabajo manual y control del gasto. Técnicamente, la clase lo conecta con variables, módulos y blueprints. Nuestro POC reutiliza el módulo de aplicación en dos copias, pero esas copias sirven la misma tienda y comparten datos: no son ambientes separados de pruebas y producción. El ejemplo empresarial requeriría aislar sus recursos y datos. No atribuir al grupo una implementación de CI/CD o de entornos de producción que no existe.

</details>

**Fuentes:**

- Clase 82.08 Cloud Computing · 10-IaC_Terraform · pp. 3, 24–25 y 31–32
- https://developer.hashicorp.com/terraform/language/modules

### 10. Cambiar recursos con menos riesgo operativo

**Orador:** Juan Pablo. **Tiempo objetivo:** 60 s.

Otra situación es reemplazar un recurso importante. Podemos definir que se prepare primero el nuevo y después se retire el anterior, para diseñar una transición ordenada. También podemos proteger recursos críticos para que la herramienta bloquee un intento de eliminarlos. Son decisiones que quedan escritas antes de hacer el cambio. El beneficio es tener protecciones y un procedimiento previsto, en lugar de decidir cada paso mientras operamos. Estas capacidades ayudan a diseñar los cambios; el equipo también tiene que comprobar que la tienda siga funcionando como espera.

**Transición:** Estas decisiones pueden usar el mismo proceso aunque cambien los servicios que administramos.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

Ejemplo de adopción empresarial de la clase: al reemplazar un servidor podemos pedir que se cree primero el nuevo recurso y se retire después el anterior. Eso da una base para diseñar una transición controlada. También podemos proteger recursos críticos para que Terraform rechace un plan que intente destruirlos. El valor es expresar estas decisiones antes de operar. En Terraform son create_before_destroy y prevent_destroy, reglas que la clase explica en la página 30. No hace falta pronunciar su sintaxis en la exposición. Son capacidades del producto y no nuevas pruebas del POC. El orden de creación no garantiza continuidad del servicio: salud, tráfico y capacidad deben resolverse en el diseño. La protección de bajas requiere mantener la regla en la configuración; no es un backup ni evita cualquier pérdida de datos. Terraform también puede modificar recursos existentes: el enfoque inmutable se elige donde corresponde.

</details>

**Fuentes:**

- Clase 82.08 Cloud Computing · 10-IaC_Terraform · pp. 4 y 30
- https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle

### 11. Una herramienta para distintos servicios

**Orador:** Juan Pablo. **Tiempo objetivo:** 50 s.

La misma forma de trabajar puede aplicarse a distintos servicios de una empresa: recursos en la nube, equipos propios o servicios externos. Terraform se conecta con ellos para administrar los recursos que definimos. Eso permite conservar un proceso común de revisión y ejecución, aunque cambien las plataformas. En The Store lo usamos con los servicios de AWS y con el despliegue de la aplicación. Adaptar una solución a otro proveedor puede requerir cambios, pero el equipo conserva la herramienta y el método de trabajo.

**Transición:** Antes de ejecutar esas acciones, podemos examinar su impacto con plan.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

Terraform usa providers para comunicarse con las APIs de plataformas y servicios. Existen providers para AWS, Azure, GCP y Kubernetes, entre otros. El equipo conserva una herramienta y un flujo de trabajo comunes aunque gestione distintos servicios. También puede administrar servicios en equipos propios y SaaS, como VMware, GitHub y Datadog. En el POC se usan AWS y Kubernetes; los demás ejemplos muestran el alcance del producto, no despliegues realizados por nosotros. El enfoque es declarativo: expresamos los recursos y sus relaciones, y Terraform calcula las acciones. Un provider diferente puede requerir recursos y configuración diferentes; no se debe prometer mover la solución entre nubes sin adaptación. La capacidad valiosa es mantener el proceso de definición, revisión y aplicación en la misma herramienta.

</details>

**Fuentes:**

- Clase 82.08 Cloud Computing · p. 14 · características Terraform
- https://developer.hashicorp.com/terraform/intro

### 12. Revisar antes de cambiar

**Orador:** Juan Pablo. **Tiempo objetivo:** 75 s.

El proceso tiene cuatro operaciones principales. Primero preparamos la herramienta para trabajar. Después pedimos un plan: una vista previa de lo que se agregaría, cambiaría o eliminaría. Ese paso permite revisar el impacto sin ejecutar todavía esas acciones. Si el cambio es el que buscamos, lo aplicamos y comprobamos el resultado. Cuando un entorno deja de hacer falta, podemos retirar sus recursos con una revisión similar. Durante la demo vamos a usar estos nombres breves: init, plan, apply y destroy. Lo importante es la decisión que permite cada uno: preparar, revisar, hacer el cambio o retirar.

**Transición:** Para calcular y ordenar estos cambios, Terraform utiliza estado y dependencias.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

init prepara la raíz terraform/, descarga providers y conecta el backend S3. plan consulta y propone cambios; apply ejecuta un plan guardado o calcula otro si no se proporciona. destroy elimina los recursos administrados por esa configuración, tras revisar el alcance. El proyecto actual usa una sola raíz y un solo estado S3 con cifrado, versionado y bloqueo nativo. scripts/acceso-kind.sh se invoca desde Terraform para preparar el acceso a ambos kind. Tras cada caso se comprueban la tienda, ambas copias y la convergencia de configuración. Ninguna de esas verificaciones se ejecuta al generar este documento.

</details>

**Fuentes:**

- https://developer.hashicorp.com/terraform/cli/commands/plan
- https://developer.hashicorp.com/terraform/cli/commands/apply
- https://developer.hashicorp.com/terraform/cli/commands/destroy
- https://developer.hashicorp.com/terraform/cli/state

### 13. Saber qué existe y en qué orden cambiarlo

**Orador:** Juan Pablo. **Tiempo objetivo:** 60 s.

Para organizar los cambios, Terraform necesita saber qué recursos están bajo su administración y cómo se relacionan con nuestra definición. Mantiene un registro que el equipo puede compartir, para trabajar con una base común. También ordena las tareas: primero tiene que existir una red, después sus conexiones y luego los servidores que las usan. Así el operador no tiene que coordinar cada paso manualmente. En The Store ese registro se guarda de forma compartida y protegida. El equipo sigue revisando quién opera y qué cambios se aplican.

**Transición:** Estas capacidades se concretan en la arquitectura de nuestra tienda.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

El estado vincula las direcciones de configuración con los recursos administrados. En el repo actual hay una sola configuración terraform/ y un backend S3 cifrado y con bloqueo nativo; el bucket tiene versionado según la preparación del README. Las referencias y depends_on expresan el orden entre módulos y recursos. El estado y su historial no son backups de la aplicación ni de las bases. El equipo debe coordinar operadores y verificar los resultados.

</details>

**Fuentes:**

- Clase 82.08 Cloud Computing · p. 14 · características Terraform
- https://developer.hashicorp.com/terraform/language/state/purpose
- https://developer.hashicorp.com/terraform/internals/graph
- terraform/providers.tf · backend remoto

### 14. Una tienda, dos copias y datos compartidos

**Orador:** Juan Pablo. **Tiempo objetivo:** 60 s.

En nuestra solución el cliente entra por un punto común que reparte las solicitudes entre dos copias de la tienda. Cada copia corre en un servidor privado y ambas utilizan los mismos servicios de datos. Terraform administra los recursos que componen esa solución y los cambios sobre la aplicación. Las dos copias son independientes: una no aumenta los recursos de la otra. Este es el entorno sobre el que vamos a demostrar cómo detectamos una diferencia, ajustamos la configuración, cambiamos de versión y aislamos una parte cuando hace falta.

**Transición:** Con esta base, podemos mostrar cuatro decisiones operativas concretas.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

Este es el mapa suficiente para entender la solución. El usuario llega a un balanceador público de AWS, el ALB. El balanceador distribuye las solicitudes entre dos EC2 privadas, una en cada zona. Dentro de cada máquina corre un kind con una copia completa de los cinco servicios. Los datos administrados son compartidos por ambas copias: MySQL para Catalog, PostgreSQL para Orders, Redis para Checkout, DynamoDB para Cart y SQS para eventos de Orders. Terraform administra la red, el cómputo, los datos y los objetos Kubernetes. Los kind son independientes: no se trasladan pods de una EC2 a la otra. Aumentar réplicas de UI no aumenta la CPU ni la memoria física. La separación de zonas permite tener dos copias detrás del ALB, pero no debe presentarse como una demostración completa de alta disponibilidad de producción. Los puertos, CIDR, acceso SSM y políticas de red están en los anexos para responder preguntas.

</details>

**Fuentes:**

- Preentrega vigente · secciones 2–4
- README · implementación EC2 + kind

### Opcional. Slide de uso de IA · oculta/opcional

**Orador:** A definir. **Tiempo objetivo:** 0 s.

Lámina opcional y oculta por pedido del usuario. Conserva únicamente el texto marcador. Completar con usos reales y validación del grupo antes de habilitarla. Si se incorpora, usar hasta 30 segundos del margen de transición.

### 15. Demo en vivo

**Orador:** Federico. **Tiempo objetivo:** 660 s.

Cambiar a la tienda y la terminal. Los cuatro casos se realizan compartiendo pantalla y no tienen láminas individuales. Entorno creado con antelación; una sola persona opera. Mostrar la acción, el plan y el efecto de cada caso, restaurando el baseline antes de continuar. Abrir catálogo y confirmar compra de prueba si el ensayo permite incluirla. El tiempo total de 11 minutos incluye presentación de entorno y los cuatro casos.

**Operador / demo:**

Ver la sección Cuatro casos para compartir pantalla.

**Transición:** Después de la demostración, volver a la lámina de cierre.

**Fuentes:**

- Preentrega vigente · sección 3

### 16. Una forma más controlada de operar The Store

**Orador:** Matias. **Tiempo objetivo:** 45 s.

La propuesta es adoptar Terraform para automatizar tareas, repetir configuraciones conocidas y revisar los cambios antes de ejecutarlos. También nos permite conservar historial, expresar reglas de acceso y reutilizar un modelo para otras necesidades. La clase muestra que estas capacidades pueden servir para preparar pruebas, ampliar entornos y diseñar cambios con protecciones. Nuestro proyecto las conecta con una tienda concreta. El valor que buscamos es que operar y hacer cambios sea un proceso que el equipo pueda entender, repetir y comprobar.

**Transición:** Abrimos las preguntas.

<details><summary>Respaldo para preguntas — no leer como guion</summary>

Cerrar con la propuesta de adopción de Terraform. Para entregar: automatización y consistencia. Para controlar: versiones, seguridad revisable y documentación del estado esperado. Para reutilizar: módulos y recursos temporales que podemos retirar cuando dejan de ser necesarios. La herramienta concreta aporta providers, lenguaje declarativo, plan, estado y resolución de dependencias. La demostración conecta esas capacidades con The Store. La decisión propuesta es incorporar Terraform al proceso del equipo, con revisión y pruebas. El POC usa AWS Academy y dos kind independientes; la adopción productiva requiere resolver los límites de capacidad, TLS y operación que figuran en el respaldo. No atribuir porcentajes de ahorro o resultados que no se hayan medido.

</details>

### 17. Preguntas

**Orador:** Todos. **Tiempo objetivo:** 0 s.

Reservar cinco minutos finales. Los tres integrantes deben poder explicar la solución completa. La navegación a los anexos está vinculada desde esta lámina. Abrir solo el respaldo relacionado con la consulta. El PPT contiene notas del orador y una lámina opcional de IA oculta.

**Fuentes:**

- https://github.com/mrossisei/the-store-iac

### Anexo. Qué cubre el POC y qué requiere otro trabajo · oculta/opcional

**Orador:** Todos. **Tiempo objetivo:** 0 s.

El POC usa dos EC2 privadas, cada una con kind independiente, ALB, datos compartidos, imágenes y aplicación administrados desde terraform/. EKS, HTTPS público, CI/CD, observabilidad, autoescalado y roles separados por servicio quedan fuera del alcance. Se reutilizan LabRole y LabInstanceProfile. Las réplicas internas no reprograman pods entre EC2. Consultar README y la preentrega vigente para los límites y la preparación.

**Fuentes:**

- Preentrega vigente · secciones 2–3
- README · alcance

### Anexo. Red y recorrido de una solicitud · oculta/opcional

**Orador:** Juan Pablo. **Tiempo objetivo:** 0 s.

Cada AZ tiene subred pública, privada y de datos. ALB y NAT están en las públicas. Cada privada tiene una EC2 sin IP pública y la interfaz del endpoint SQS. Las subredes de datos alojan RDS/Redis y no tienen ruta por defecto a Internet. Las privadas salen por el NAT de su propia zona. Hay endpoints Gateway para S3/DynamoDB e Interface para SQS. El ALB acepta HTTP/80 y solo él puede alcanzar EC2:8080 según SG. kind mapea host8080 a NodePort30080 y la UI escucha8080. SG de datos permite MySQL3306, PostgreSQL5432 y Redis6379 solo desde EC2. Los CIDR de pods y Services son internos de cada kind, no subredes AWS y no deben interpretarse como red compartida entre las EC2. Administración autenticada con SSM y TLS hacia las dos APIs, usando los puertos locales16443 y26443.

**Fuentes:**

- Preentrega vigente · sección 4
- terraform/terraform.tfvars
- README y configuración Terraform

### Anexo. Una configuración y un estado compartido · oculta/opcional

**Orador:** Juan Pablo. **Tiempo objetivo:** 0 s.

La versión simplificada actual opera desde terraform/ con un estado S3: the-store/kind/terraform.tfstate. main.tf conecta red, imágenes, cómputo, datos y dos instancias del módulo de aplicación. El bucket debe existir antes de init y su preparación está en README. El backend habilita encrypt y use_lockfile; el bucket se configura con versionado. Terraform invoca scripts/acceso-kind.sh para esperar los clústeres y abrir túneles SSM a sus API. El retiro se solicita desde la misma raíz con destroy, revisando las dependencias y el plan. Auditar recursos después; el bucket del estado y los roles preexistentes se conservan fuera de esa destrucción. Retirar datos administrados puede eliminarlos; el estado versionado no reemplaza sus backups. No proyectar estados o kubeconfigs completos.

**Fuentes:**

- README.md · cómo levantar y destruir
- terraform/providers.tf
- terraform/main.tf

### Anexo. Por qué elegimos esta combinación · oculta/opcional

**Orador:** Todos. **Tiempo objetivo:** 0 s.

La preentrega compara Pulumi con Terraform: el grupo eligió HCL, ya conocía Terraform y valoró el ecosistema. Eso no implica que Pulumi no pueda gestionar la arquitectura. También compara NLB más nginx con ALB: para el tráfico HTTP de esta tienda el ALB evita agregar un proxy que deba mantenerse. kind en EC2 es el alcance aprobado vigente, con un clúster independiente por host. No heredar las decisiones de los documentos antiguos sobre EKS/NLB. Las limitaciones del Lab condicionan tamaños y permisos. No decir que kind no es Kubernetes real: usa su API y nodos en contenedores. El costo no está actualizado ni medido para la presentación, por eso no se muestra el importe del diseño histórico.

**Fuentes:**

- Preentrega vigente · secciones 2, 3 y 5

### Anexo. Gestionar también lo que ya está creado · oculta/opcional

**Orador:** Juan Pablo. **Tiempo objetivo:** 0 s.

Terraform permite operar sobre recursos existentes. El plan detecta diferencias de los atributos que el provider consulta y administra; no es un monitor continuo de cualquier cambio. Import o un bloque import vincula un recurso ya existente al estado; debe acompañarse de configuración apropiada y revisión. No demostramos importación en los cuatro casos. plan -replace=ADDRESS solicita planificar la sustitución de un recurso y puede afectar el servicio; tampoco se ejecuta en la demo. plan -destroy deja ver el alcance de una eliminación sin realizarla. No usar -target como forma rutinaria de aplicar una parte aislada del proyecto. El rollback mostrado selecciona imágenes anteriores; no es una restauración universal de infraestructura ni de datos.

**Fuentes:**

- https://developer.hashicorp.com/terraform/cli/commands/import
- https://developer.hashicorp.com/terraform/cli/commands/plan
- https://developer.hashicorp.com/terraform/cli/commands/destroy

### Anexo. Fuentes y documentación de respaldo · oculta/opcional

**Orador:** Todos. **Tiempo objetivo:** 0 s.

La clase adjunta 10-IaC_Terraform.pptx (1).pdf, de 82.08 Cloud Computing, aporta ventajas y capacidades generales. La preentrega vigente de Redes de Información es la autoridad de integrantes, legajos y alcance. Se contrastó el respaldo operativo con la versión simplificada actual en main: una configuración terraform/, un backend S3 y scripts/acceso-kind.sh. Los ejemplos empresariales ilustran adopción y no son nuevos ambientes implementados. No se ejecutaron operaciones AWS ni demos al generar esta presentación.

**Fuentes:**

- https://developer.hashicorp.com/terraform/intro
- https://developer.hashicorp.com/terraform/cli/commands/plan
- https://developer.hashicorp.com/terraform/cli/commands/apply
- https://developer.hashicorp.com/terraform/cli/state
- https://developer.hashicorp.com/terraform/language/modules
- https://developer.hashicorp.com/terraform/language/state/purpose
- https://developer.hashicorp.com/terraform/internals/graph
- https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle
- https://developer.hashicorp.com/terraform/language/backend/s3
- https://developer.hashicorp.com/terraform/cli/commands/import
- https://developer.hashicorp.com/terraform/cli/commands/destroy
- https://github.com/mrossisei/the-store-iac

## Cuatro casos para compartir pantalla — sin diapositivas

### Un cambio manual también debe ser visible

Cambiar solo la etiqueta Name de la VPC del proyecto desde la consola AWS, de the-store a the-store-demo. Revisar que plan proponga restaurar ese nombre sin otras acciones inesperadas. Aplicar, comprobar el nombre original y repetir plan. Terraform detecta diferencias al planificar; no vigila continuamente el entorno.

**Operador:**

Identificar por ID la VPC del proyecto antes de exponer. Desde la consola cambiar únicamente Name. Desde la raíz del repo: terraform -chdir=terraform plan; terraform -chdir=terraform apply, revisando su nuevo plan antes de confirmar; volver a ejecutar plan. El proyecto usa una sola configuración. No proyectar estados completos ni datos sensibles.

### Más réplicas de UI, con un cambio revisable

Cambiar replicas.ui de 2 a 4 en terraform/terraform.tfvars, manteniendo los otros servicios en 2. Revisar plan y aplicar. Comprobar cuatro réplicas disponibles de UI en ambos kind y la respuesta de la tienda. El total previsto de pods app cambia de 20 a 24; siguen existiendo dos EC2. Volver a ui=2 y comprobar el baseline. La prueba no aumenta CPU ni memoria de los hosts ni mide rendimiento.

**Operador:**

Ejecutar terraform -chdir=terraform plan y terraform -chdir=terraform apply. Inspeccionar A y B con kubectl --kubeconfig .local/kind-a.kubeconfig get deployment,pods -n the-store y el comando equivalente para kind-b. Esperar réplicas disponibles, no solo deseadas. Restaurar ui=2, revisar/aplicar y comprobar.

### Publicar una versión y poder volver

Seleccionar app_version v1, luego v2 y volver a v1. Las dos versiones deben haberse publicado durante la preparación inicial en ECR con tags inmutables. Cambiar solo la selección actualiza las imágenes de los Deployments; comprobar en plan que no se reconstruyan imágenes durante el caso. Mostrar The Store · v1/v2 en el encabezado, el rollout de ambas copias y la respuesta de la tienda. El frontend original conserva su diseño: se agregó esa identificación de versión para la demo. Volver a una imagen anterior no revierte datos ni migraciones y no garantiza por sí solo ausencia de interrupciones.

**Operador:**

Editar app_version en terraform/terraform.tfvars, revisar plan y aplicar desde terraform/. Comprobar A/B con sus kubeconfigs y abrir /catalog. Usar v1→v2→v1; verificar las imágenes esperadas al regresar. Para afirmar continuidad hace falta una medición real ensayada, no solo una respuesta final de UI.

### Aislar Checkout y conservar catálogo y carrito

Simular la decisión de aislar Checkout agregándolo a quarantine. El plan debe limitar el cambio a NetworkPolicies en ambos kind. Comprobar catálogo y carrito funcionales y compra bloqueada, con sondas válidas. Vaciar quarantine, revisar y aplicar, y comprobar una compra real. No se simula un ataque real. Si se afirma que no hubo reinicios, comparar UID y restartCount antes/después. No aceptar cualquier timeout como evidencia de aislamiento.

**Operador:**

Editar quarantine=[] → ["checkout"] → [] en terraform/terraform.tfvars; plan y apply en cada transición. Mostrar el efecto por navegador y revisar ambas copias. Mantener una sola persona operando. Restaurar el baseline y comprobar compra antes de cerrar.

## Preparación de la demo

La implementación vigente usa **una sola raíz `terraform/` y un estado remoto S3**. Los comandos de este guion se ejecutan desde la raíz del repositorio. El detalle de preparación está en README.md. Esta generación solo produce documentos: no certifica pruebas nuevas ni ejecuta AWS.

### Antes de exponer

1. Preparar el bucket y el backend siguiendo README; no crear un bucket adicional para ocultar errores de permisos.
2. Tener credenciales vigentes, presupuesto y tiempo de sesión suficientes en AWS Academy.
3. Crear el entorno con antelación. Terraform construye/publica v1/v2 en la preparación inicial y crea los recursos; no esperar esa creación durante la exposición.
4. Confirmar UI=2 por kind, versión v1 y quarantine=[]. Comprobar las dos copias, los dos targets del ALB y una compra real.
5. Preparar el navegador en la tienda, la consola en la VPC propia y el editor en terraform/terraform.tfvars.
6. Ensayar los cuatro casos y guardar capturas o video reales, asociados a versión/commit. No usar diagramas como evidencia.
7. Verificar pantalla compartida y VPN; una sola persona opera el entorno. No mostrar claves, contraseñas, estados completos o kubeconfigs.

### Preparación y operación

Con el backend inicializado según README:

```bash
terraform -chdir=terraform plan
terraform -chdir=terraform apply
terraform -chdir=terraform output url
```

En plan/apply, Terraform invoca scripts/acceso-kind.sh para comprobar los kind y abrir los túneles. El primer despliegue puede tardar varios minutos. Durante los casos, revisar el plan completo para detectar altas, bajas o reemplazos inesperados. Si se ejecuta apply sin un plan guardado, se calcula un nuevo plan y se revisa antes de confirmar.

### Inspección de ambas copias

Los kubeconfigs privados quedan bajo .local/. Sin mostrar su contenido:

```bash
kubectl --kubeconfig .local/kind-a.kubeconfig get deployment,pods -n the-store
kubectl --kubeconfig .local/kind-b.kubeconfig get deployment,pods -n the-store
```

Identificar A y B explícitamente. Si el acceso falla, diagnosticar el túnel antes de interpretar resultados de la aplicación. No imprimir Secrets ni planes/estados completos frente al público.

### Lista de comprobación por caso

| Caso | Cambio | Lo que se debe observar | Vuelta al inicio |
|---|---|---|---|
| Drift | Name de la VPC desde consola | Plan propone restaurar solo esa etiqueta | Name original y plan sin cambios |
| Réplicas | UI 2→4 por kind | UI disponible 4/4 en ambos; 24 pods app; 2 EC2 | UI 2; 20 pods app |
| Versión | app_version v1→v2 | Etiqueta visible, rollout e imágenes en ambas copias | v1 e imágenes esperadas |
| Cuarentena | checkout en quarantine | Cambian policies; catálogo/carrito sanos; compra bloqueada | Lista vacía y compra real |

Todos los parámetros están en terraform/terraform.tfvars. Los números describen el caso previsto, no pruebas ejecutadas al generar el PPT. Cambiar app_version selecciona una versión ya publicada: confirmar en plan que no haya reconstrucciones inesperadas. La etiqueta de versión del frontend se agregó para observar ese caso; no es un rediseño de la tienda.

### Si se supera el tiempo ensayado

Pasar a una grabación real del mismo caso e identificarla como respaldo. Si falta evidencia, no atribuir un resultado. Restaurar el baseline antes de seguir y reservar margen para el cierre.

### Al terminar

Revisar el alcance y ejecutar el procedimiento actual:

```bash
terraform -chdir=terraform plan -destroy
terraform -chdir=terraform destroy
```

Después auditar recursos por IDs/tags. El bucket remoto y los roles preexistentes permanecen. El destroy de esta configuración incluye los recursos que administra; no asumir que conserva ECR, bases o datos. No iniciar la destrucción durante la demo.

## Regeneración

```bash
python3 -m venv /tmp/ppt-terraform-venv
/tmp/ppt-terraform-venv/bin/pip install python-pptx==1.0.2
/tmp/ppt-terraform-venv/bin/python scripts/generar-presentacion.py
```

Exportar el PPT a PDF sin las láminas ocultas para el recorrido principal. Exportar los anexos aparte. Los textos y diagramas siguen siendo editables. La correspondencia con la clase se documenta en docs/referencia-clase-terraform.md.