# Decisiones de diseño

Por qué se eligió cada cosa, qué alternativas se evaluaron y qué limitaciones tiene la
solución. Sirve para responder las preguntas de la defensa oral: cada decisión está pensada
para poder justificarse en una o dos frases.

---

## 1. Terraform como herramienta de IaC

**Qué se eligió.** Terraform (lenguaje HCL) con los providers `docker`, `kind`, `kubernetes`,
`helm` y `random`.

**Por qué.** Es el estándar de la industria para infraestructura declarativa: se describe el
estado deseado, la herramienta calcula la diferencia contra la realidad (`plan`) y la aplica en
el orden correcto (`apply`). Eso es exactamente lo que le falta al script `local.sh` que provee
la cátedra, que es imperativo: sólo sabe crear todo o borrar todo.

**Alternativas.** *Pulumi* hace lo mismo con lenguajes de propósito general; se descartó porque
HCL es más legible y su plan es más directo de revisar en vivo. *OpenTofu* es la bifurcación
libre de Terraform y el código funciona igual, pero el tema asignado nombra a Terraform.
*Ansible* no mantiene estado ni produce un plan. *Helm* y *Kustomize* sólo llegan a los objetos
de Kubernetes: no crean la red ni el clúster (de hecho usamos Helm **desde** Terraform para el
Ingress Controller).

## 2. Clúster local con kind en lugar de una nube pública

**Qué se eligió.** Un clúster de Kubernetes creado con kind (*Kubernetes IN Docker*) en la
propia máquina.

**Por qué.** Tres razones: no tiene costo (la cátedra aclara que los costos corren por cuenta
del grupo); no depende de credenciales, cuotas ni conectividad durante una demostración que es
remota; y deja a la vista toda la capa de red —direccionamiento, NAT, ruteo entre nodos, DNS
interno y filtrado— que es lo que interesa en esta materia y que un servicio administrado
esconde. Además es la misma plataforma que usa el script provisto por la cátedra, así que la
comparación "antes y después" es directa.

**Alternativa.** Desplegar en AWS con VPC, EKS, RDS y ElastiCache. Es más parecido a un entorno
productivo, pero cuesta dinero por hora, agrega puntos de falla externos en la demo y oculta la
red detrás de servicios administrados. La estructura modular deja ese camino abierto: para
migrar habría que reemplazar los módulos `networking` y `cluster` y publicar las imágenes en
un registry; los módulos `databases` y `application` no cambian.

## 3. kind y no minikube ni k3d

minikube levanta por defecto un solo nodo, con lo cual no habría tráfico entre nodos que
mostrar. k3d usa k3s, una distribución reducida que trae su propio balanceador y controlador de
Ingress ya integrados, es decir que resuelve por su cuenta justo lo que queremos declarar
nosotros. kind ejecuta Kubernetes sin modificaciones, permite declarar la topología y los
bloques de direcciones, y es el que usa la cátedra.

## 4. Un solo estado con cuatro módulos

**Qué se eligió.** Un único directorio raíz (`terraform/`) con `main.tf`, `variables.tf`,
`outputs.tf`, `providers.tf` y `terraform.tfvars`, que invoca cuatro módulos: `networking`,
`cluster`, `databases` y `application`.

**Por qué.** Con un solo estado, `terraform apply` crea el entorno completo y `terraform
destroy` lo elimina completo: es lo más simple de explicar y de demostrar. Medido en la
notebook: el `destroy` tarda unos 20 segundos y no deja contenedores, redes, volúmenes ni
imágenes; el `apply` desde cero tarda unos 15 minutos la primera vez (compilación de las
imágenes) y unos 3 minutos las siguientes. Los módulos separan responsabilidades y permiten que
el código se lea como la arquitectura: red, clúster, datos y aplicación.

**Alternativa.** Separar en varios estados independientes (uno por capa). Es lo que se hace en
equipos grandes, porque reduce el radio de impacto de un error y permite permisos distintos por
capa, pero obliga a coordinar los estados entre sí y complica la demostración. Para un POC de
un solo entorno no se justifica.

## 5. Bloques de direcciones

**Qué se eligió.** Nodos en `172.30.0.0/24`, pods en `10.244.0.0/16` (un /24 por nodo) y
Services en `10.96.0.0/16`.

**Por qué.** Los tres son rangos privados (RFC 1918) y son **disjuntos entre sí y con la red
local de la máquina** (192.168.x.x). Si dos de esos bloques se solaparan, el kernel no sabría
por qué interfaz enviar un paquete y la conectividad fallaría de forma intermitente. Se usó un
/24 para los nodos porque 254 direcciones sobran para tres nodos y deja el resto del espacio
libre; 10.244.0.0/16 y 10.96.0.0/16 son los valores convencionales de Kubernetes, lo que hace
el entorno reconocible para cualquiera que lo inspeccione.

**Detalles.** La red de Docker se llama obligatoriamente `kind`: la librería que crea el clúster
busca una red con ese nombre y, si existe, la reutiliza. Así somos nosotros los que fijamos el
bloque en lugar de dejar que lo elija la herramienta. Las direcciones concretas de cada nodo
(.2, .3, .4) las asigna Docker en el orden en que se crean los contenedores, que no es
determinístico: por eso el diagrama las marca como ejemplo. Se pueden ver con
`docker network inspect kind`.

## 6. Ingress Controller con hostPort

**Qué se eligió.** ingress-nginx corriendo en el nodo de control (que hace de nodo de borde),
escuchando en los puertos 80 y 443 del nodo, que kind publica hacia la máquina.

**Por qué.** En un clúster local no hay un balanceador de nube que asigne una IP pública. El
patrón `hostPort` + publicación de puertos es el que documenta kind y permite entrar por
`http://the-store.localhost` sin puertos raros. Además el Ingress es un balanceador de capa 7:
enruta según el nombre de host, algo que un Service de capa 4 no puede hacer.

**Alternativas.** *NodePort* obligaría a usar puertos altos (30000-32767) en la URL.
*MetalLB* permitiría usar Services de tipo LoadBalancer con ARP, que es interesante para la
materia, pero agrega un componente más y no funciona igual fuera de Linux.

## 7. Bases de datos dentro del clúster

**Qué se eligió.** MariaDB para Catalog, PostgreSQL para Orders y Redis para Checkout, como
StatefulSets con disco persistente de 1 GiB. Cart y la mensajería de Orders usan los
proveedores en memoria que la propia aplicación trae.

**Por qué.** Un StatefulSet es el objeto de Kubernetes pensado para aplicaciones con estado: da
identidad estable al pod y le asocia un disco propio, de modo que los datos sobreviven al
reinicio. Se eligieron tres motores distintos para mostrar tres protocolos distintos en el
diagrama (MySQL, PostgreSQL y RESP). Cart y la mensajería quedaron en memoria para acotar el
alcance del POC: el backend original de Cart es DynamoDB, un servicio propietario que no aporta
nada nuevo al análisis de red.

**Alternativa.** Servicios administrados de una nube (RDS, ElastiCache). Se descartó junto con
la decisión 2.

## 8. Imágenes construidas desde el código fuente

**Qué se eligió.** Terraform construye las cinco imágenes con el provider de Docker a partir
del código que provee la cátedra y las carga en los nodos del clúster con `kind load`.

**Por qué.** Es lo mismo que hace `local.sh`, de modo que estamos desplegando exactamente la
aplicación que nos dieron, y el tag de la imagen queda como variable (`app_version`), lo que
habilita el caso de uso de actualización y rollback (medido: cambiar de versión y hacer el
*rolling update* de los cinco servicios tarda menos de un minuto porque Docker reutiliza la
caché de compilación).

**Limitación conocida.** La carga de imágenes se hace con un `local-exec`, que es un comando
imperativo dentro de Terraform y requiere tener instalado el binario `kind`. Es la única parte
del código que no es declarativa: el provider de kind todavía no expone un recurso para esto.
La alternativa sería levantar un registry de imágenes local, lo que agregaría un componente y
configuración adicional en cada nodo. Nota: `terraform destroy` borra también las imágenes
locales, así que el `apply` siguiente las vuelve a construir.

## 9. Contraseñas generadas por Terraform

**Qué se eligió.** Las contraseñas de MariaDB y PostgreSQL las genera el provider `random` y se
inyectan como variables de entorno tanto en la base como en el microservicio que la consume.

**Por qué.** No hay credenciales escritas en el código ni en el repositorio, y cada despliegue
usa contraseñas distintas.

**Limitación conocida.** Las contraseñas quedan visibles en la definición de los objetos de
Kubernetes y en el archivo de estado de Terraform. En un entorno productivo se usarían Secrets
de Kubernetes con cifrado en reposo o un gestor externo (Vault, AWS Secrets Manager), y el
estado se guardaría en un backend remoto cifrado.

## 10. Segmentación con NetworkPolicies

**Qué se eligió.** Cinco reglas, basadas en dos etiquetas de cada pod (`app`, el nombre del
servicio, y `tier`, la capa: frontend, backend o data):

1. por defecto ningún pod acepta conexiones entrantes;
2. la UI acepta sólo las del Ingress Controller;
3. los backends aceptan sólo las de la UI y de otros backends;
4. cada base de datos acepta sólo las del microservicio que la usa (catalog-db de catalog,
   orders-db de orders, checkout-db de checkout);
5. un pod con `tier = cuarentena` no puede recibir ni iniciar ninguna conexión.

**Por qué.** Kubernetes **no aísla nada por defecto**: sin políticas, cualquier pod puede
hablar con cualquier otro, incluso de otro namespace. Estas reglas implementan el principio de
mínimo privilegio en tres capas, que es el equivalente de los *security groups* de una nube o
de las ACL de un firewall. La regla 4 es más estricta que "las bases aceptan tráfico de los
backends": con esa versión, un servicio que no usa base de datos (carts) podía conectarse a
`orders-db`, cosa que se comprobó y se cerró.

**Cómo funciona la cuarentena.** La variable `quarantine` lista los servicios comprometidos.
Terraform cambia la etiqueta `tier` de esos pods a `cuarentena`; como todas las reglas de
permiso se basan en `tier`, el pod deja de coincidir con ellas y queda cubierto sólo por la
denegación por defecto y por la regla 5, que además le bloquea la salida (incluida Internet).
Es un cambio de una línea en `terraform.tfvars`, el plan muestra un único recurso modificado y
el resto de la tienda sigue funcionando.

**Alcance.** Salvo para la cuarentena, se filtra sólo el tráfico entrante (`Ingress`), no el
saliente. Filtrar también la salida obliga a habilitar explícitamente el DNS y cada destino
externo, lo que multiplica las reglas sin agregar valor al POC.

## 11. Estado de Terraform local

Se usa el backend local, que ya provee bloqueo para evitar dos ejecuciones simultáneas. Para
trabajar en equipo correspondería un backend remoto (S3 con versionado y bloqueo, o Terraform
Cloud): son cinco líneas de configuración, que quedaron como ejemplo comentado en
`providers.tf`, y no cambia el resto del código. No se activó para el POC porque requiere una
cuenta de nube.

## 12. Cantidad de réplicas fija; cantidad de nodos fija al crear el clúster

Las réplicas de cada microservicio se declaran en `terraform.tfvars`. Escalar es cambiar un
número y aplicar. No se usó autoescalado automático (HPA) porque agrega un componente más
(servidor de métricas) y porque el caso de uso que queremos mostrar es justamente el control
explícito del tamaño del entorno desde el código.

La cantidad de nodos worker también es una variable, pero kind **no permite agregar nodos a un
clúster existente**: cambiar `worker_count` hace que Terraform planifique recrear el clúster
completo (se ve como `must be replaced` en el plan). Por eso el caso de uso de escalamiento
habla de réplicas y no de nodos. En una nube, el grupo de nodos sí se escala en caliente.

---

## Preguntas probables y dónde está la respuesta

| Pregunta | Decisión |
|---|---|
| ¿Por qué Terraform y no Pulumi o Ansible? | 1 |
| ¿Por qué no lo hicieron en la nube? ¿Cómo lo migrarían? | 2 |
| ¿Por qué kind y no minikube? | 3 |
| ¿Por qué un solo estado? ¿Cuánto tarda crear y destruir? | 4 |
| ¿Por qué esos bloques de direcciones? ¿Qué pasa si se solapan? ¿Por qué el nodo de control no es siempre .2? | 5 |
| ¿Cómo entra el tráfico desde afuera? ¿Qué capa balancea cada cosa? | 6 |
| ¿Dónde se guardan los datos? ¿Sobreviven a un reinicio? | 7 |
| ¿De dónde salen las imágenes? ¿Cómo actualizan una versión? | 8 |
| ¿Dónde están las credenciales? | 9 |
| ¿Kubernetes aísla los pods por defecto? ¿En qué capa filtran las políticas? ¿Cómo funciona la cuarentena? | 10 |
| ¿Qué pasa si dos personas aplican a la vez? | 11 |
| ¿Cómo escalan ante un pico de tráfico? ¿Y agregar nodos? | 12 |
