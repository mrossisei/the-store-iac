# Guía para el grupo: entender Terraform y este repositorio

Para quien nunca usó Terraform ni Kubernetes. Se lee en una tarde con el repo abierto al lado.

---

## 1. Qué es Terraform

Terraform es una herramienta de **Infraestructura como Código**. En lugar de crear las cosas a
mano (clics en una consola, comandos sueltos, un script de bash), escribís en archivos de texto
**cómo querés que quede** la infraestructura: "una red con este bloque de direcciones, un
clúster con tres nodos, un servicio con dos copias de esta imagen". Eso se llama enfoque
**declarativo**: describís el resultado, no los pasos.

Terraform lee esos archivos, consulta cómo está la realidad (a través de los **providers**, que
son plugins que hablan con la API de Docker, de Kubernetes, de AWS, etc.), guarda lo que creó
en un archivo de **estado**, y calcula un **plan**: la diferencia entre lo que hay y lo que
pediste. Después ejecuta ese plan (`apply`) creando, modificando o borrando sólo lo necesario y
en el orden correcto. Dos consecuencias importantes:

- **Idempotencia:** si aplicás dos veces sin cambiar nada, la segunda no hace nada.
- **Detección de drift:** si alguien tocó algo a mano, el próximo `plan` lo muestra y el
  `apply` lo corrige.

En este TP, Terraform reemplaza al script `local.sh` que provee la cátedra.

## 2. Vocabulario mínimo

| Término | Qué es | Ejemplo en el repo |
|---|---|---|
| **Provider** | Plugin que habla con una plataforma | `docker`, `kind`, `kubernetes`, `helm` (ver `providers.tf`) |
| **Resource** | Un objeto que Terraform crea y administra | `resource "docker_network" "this"` |
| **Variable** (`var.x`) | Un parámetro de entrada | `var.worker_count` |
| **tfvars** | Archivo con los valores de las variables | `terraform.tfvars` |
| **Local** (`local.x`) | Un valor calculado para no repetir | `local.services` |
| **Output** | Un valor que el módulo expone hacia afuera | `output "url"` |
| **Module** | Una carpeta de código reutilizable que se invoca | `module "cluster"` |
| **State** | Archivo donde Terraform recuerda lo que creó | `terraform.tfstate` (no se sube a git) |
| **plan / apply / destroy** | Calcular el diff / ejecutarlo / borrar todo | `terraform plan` |
| **`for_each`** | Crear N copias de un recurso desde un mapa | los 5 microservicios |
| **`dynamic`** | Generar bloques repetidos desde una lista | los nodos worker, las variables de entorno |

## 3. Cómo se lee el lenguaje (HCL)

```hcl
resource "docker_network" "this" {   # tipo de objeto, y nombre interno para referenciarlo
  name   = var.network_name          # var.x  = una variable de entrada
  driver = "bridge"

  ipam_config {                      # bloque anidado: una sub-estructura del objeto
    subnet  = var.subnet
    gateway = cidrhost(var.subnet, 1)   # función incorporada: primera IP del bloque
  }
}
```

Reglas prácticas:

- `tipo.nombre.atributo` referencia a otro recurso. Si el recurso A referencia al B, Terraform
  crea B primero: **el orden lo deduce solo**.
- `module.cluster.endpoint` es el output `endpoint` del módulo `cluster`.
- `"texto ${expresión}"` interpola; `{ k = v }` es un mapa; `cond ? a : b` es un condicional;
  `[for x in lista : f(x)]` es una comprensión.
- El orden de los archivos y de los bloques **no importa**. Se separan por tema sólo para leer
  mejor.

## 4. El ciclo de trabajo

```bash
cd terraform
terraform init      # descarga los providers (una vez)
terraform plan      # muestra qué cambiaría, sin tocar nada
terraform apply     # lo ejecuta
terraform output    # muestra los resultados
terraform destroy   # borra todo lo que creó
```

Cómo se lee un plan: `+` crea, `~` modifica, `-` destruye, `-/+` recrea. La última línea
(`Plan: X to add, Y to change, Z to destroy`) es lo primero que hay que mirar.

## 5. Recorrido del código, en orden

Son unas 500 líneas en total. Leelas en este orden:

1. **`terraform/terraform.tfvars`** (20 líneas). Los valores del entorno: cuántos nodos,
   cuántas réplicas, qué bloques de red, qué versión. Es el archivo que se toca para cambiar
   algo.
2. **`terraform/variables.tf`**. Las mismas variables, pero con su tipo y su descripción. Es la
   documentación de qué se puede configurar.
3. **`terraform/modules/networking/main.tf`** (20 líneas). La red. Es el recurso más simple del
   repo: perfecto para entender la sintaxis.
4. **`terraform/main.tf`** (90 líneas). El archivo central: invoca los cuatro módulos en orden y
   construye las imágenes. Leerlo da el mapa completo de la solución.
5. **`terraform/modules/cluster/main.tf`**. El clúster: la topología de nodos, los bloques de
   pods y servicios, los puertos publicados y el Ingress Controller.
6. **`terraform/modules/databases/main.tf`**. Las tres bases de datos. Fijate en el mapa
   `locals.databases`: es una tabla donde cada fila es una base, y un único recurso con
   `for_each` las crea a todas.
7. **`terraform/modules/application/main.tf`**. Los cinco microservicios, con el mismo patrón de
   tabla + `for_each`, más el Ingress.
8. **`terraform/modules/application/network_policies.tf`**. Las cuatro reglas de segmentación de
   red. Es la parte más relacionada con la materia.
9. **`terraform/outputs.tf`** y **`providers.tf`**. Cortitos.

Lo que hay en `the-store/` es el código de la aplicación (Java, Go, Node): no lo tocamos.

## 6. Ejercicios para aprender tocando

Con el entorno levantado (`terraform apply`), todos son reversibles:

1. **Mirar el estado:** `terraform state list` muestra todo lo que Terraform administra.
   `terraform state show module.networking.docker_network.this` muestra cómo recuerda un objeto.
2. **Cambiar réplicas:** poné `catalog = 2` en `terraform.tfvars`, corré `terraform plan` (debe
   decir `~ replicas 1 -> 2`), aplicá y mirá `kubectl get pods -n the-store`.
3. **Provocar drift:** `kubectl scale deploy/catalog -n the-store --replicas=5`, después
   `terraform plan`. Terraform detecta el cambio hecho a mano y `terraform apply` lo revierte.
4. **Cambiar la versión:** poné `app_version = "1.1"`, aplicá y mirá cómo cambia la imagen de
   los cinco Deployments sin que la tienda deje de responder.
5. **Cambiar el tema visual:** poné `ui_theme = "green"` y recargá la página.
6. **Romper una regla de red:** comentá la política `databases_from_backends` y comprobá con
   `./verificar.sh` que ahora un pod ajeno sí llega a la base.

## 7. Qué es The Store y qué nos importa

**Es una página web**: una tienda online de demostración publicada por AWS para practicar
despliegues de microservicios. Está corriendo en la máquina: abrí
**http://the-store.localhost**.

Son cinco programas independientes que se hablan por HTTP:

| Servicio | Lenguaje | Qué hace | Base de datos |
|---|---|---|---|
| `ui` | Java | La página que ve el usuario; llama a los otros cuatro | — |
| `catalog` | Go | Los productos | MariaDB |
| `carts` | Java | El carrito | en memoria |
| `orders` | Java | Las órdenes de compra | PostgreSQL |
| `checkout` | Node.js | El proceso de compra; llama a `orders` | Redis |

**No nos importa** su código interno: es la carga que corre sobre nuestra infraestructura.
**Sí nos importa** cómo se empaqueta (imágenes), cómo se configura (variables de entorno
`RETAIL_*`), cómo se despliega (réplicas, puertos, chequeos de salud) y sobre todo cómo se
conectan entre sí y con el usuario (DNS interno, direcciones, NAT, Ingress, reglas de red).

Para verla por dentro:

```bash
export KUBECONFIG=~/.kube/the-store.kubeconfig
kubectl get pods -n the-store -o wide                    # dónde corre cada pieza y con qué IP
kubectl exec -n the-store deploy/ui -- curl -s http://catalog/catalogue | head -c 300
kubectl exec -n the-store deploy/ui -- curl -s http://orders/orders | head -c 300
kubectl logs -n the-store deploy/checkout --tail=20
```

## 8. Kubernetes mínimo

| Objeto | Para qué sirve |
|---|---|
| **Pod** | La unidad mínima: uno o más contenedores con una IP propia |
| **Deployment** | Mantiene N copias de un pod y hace actualizaciones sin corte |
| **StatefulSet** | Igual, pero para cosas con estado: identidad fija y disco propio |
| **Service** | Nombre DNS + IP virtual que reparte el tráfico entre las copias |
| **Ingress** | Regla HTTP: "este nombre de host va a este Service" |
| **Namespace** | Carpeta lógica. Ojo: **no aísla la red por sí solo** |
| **NetworkPolicy** | Regla de firewall entre pods |
| **kubectl** | La herramienta de línea de comandos: `get`, `describe`, `logs`, `exec` |

## 9. Herramientas

- **IntelliJ IDEA** (o cualquier IDE de JetBrains) con el plugin gratuito **"Terraform and
  HCL"**: resaltado, autocompletado de los atributos de cada provider y errores en vivo. El
  plugin **Kubernetes** permite además ver el clúster desde el IDE.
- **VS Code**: extensión "HashiCorp Terraform".
- En la terminal hacen falta `terraform`, `docker`, `kind` y `kubectl`.
- `terraform fmt -recursive` formatea el código; conviene correrlo antes de cada commit.

## 10. Para seguir leyendo

- Terraform, introducción oficial: https://developer.hashicorp.com/terraform/intro
- Referencia del lenguaje: https://developer.hashicorp.com/terraform/language
- Documentación de cada recurso: https://registry.terraform.io (buscar el provider y el recurso)
- kind: https://kind.sigs.k8s.io/docs/user/quick-start/
- Kubernetes: https://kubernetes.io/docs/concepts/
- En este repo: `docs/decisiones.md` (el porqué de cada elección) y `docs/preentrega.pdf`.
