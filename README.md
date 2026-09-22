# The Store con Terraform — Infraestructura como Código

**TP Especial · Redes de Información · ITBA · 2C 2026**
**Integrantes:** Matias Rossi, Juan Pablo Birsa, Federico Viera

Este repositorio despliega la tienda **The Store** (cinco microservicios) sobre un clúster de
Kubernetes, con **toda la infraestructura declarada en Terraform**: la red y su
direccionamiento, el clúster, el punto de entrada HTTP, las bases de datos, los microservicios
y las reglas de segmentación de red.

```bash
cd terraform
terraform init      # descarga los providers (una sola vez)
terraform plan      # muestra qué se va a crear
terraform apply     # crea todo (~15 min la primera vez, ~3 min las siguientes)
```

Después de `apply`, la tienda queda en **http://the-store.localhost**.
Para borrar todo: `terraform destroy` (~20 s, no deja contenedores, redes ni volúmenes).
Para comprobar que todo funciona: `./verificar.sh` (19 comprobaciones: compra completa,
persistencia y reglas de red).

![Arquitectura](docs/img/arquitectura.png)

## Requisitos

| Herramienta | Versión | Para qué |
|---|---|---|
| Docker | ≥ 24 | Los nodos del clúster son contenedores |
| Terraform | ≥ 1.10 | La herramienta de IaC |
| kind | ≥ 0.29 | Sólo para cargar las imágenes en los nodos |
| kubectl | 1.34–1.36 | Opcional, para inspeccionar el clúster y para `verificar.sh` |

Se necesitan además los puertos 80 y 443 libres, unos 15 GB de disco y 8 GB de RAM. En Linux
hay que subir los límites de inotify una vez (si no, tras un reinicio de la máquina el clúster
puede quedar sin red):

```bash
sudo sysctl -w fs.inotify.max_user_watches=524288 fs.inotify.max_user_instances=512
```

## Qué hay en el repositorio

```
terraform/
├── main.tf              # orquesta los módulos y construye las imágenes
├── variables.tf         # variables de entrada
├── outputs.tf           # resultados (URL, kubeconfig, bloques de red)
├── providers.tf         # docker, kind, kubernetes, helm
├── terraform.tfvars     # valores del entorno (acá se cambia todo)
└── modules/
    ├── networking/      # red 172.30.0.0/24
    ├── cluster/         # clúster Kubernetes + Ingress Controller
    ├── databases/       # MariaDB, PostgreSQL y Redis
    └── application/     # los 5 microservicios, Ingress y NetworkPolicies

verificar.sh             # comprueba que el entorno desplegado funciona
the-store/               # código fuente de la aplicación (provisto por la cátedra)
docs/                    # pre-entrega, decisiones, guía de Terraform, diagrama
```

## Documentación

| Archivo | Contenido |
|---|---|
| [`docs/preentrega.pdf`](docs/preentrega.pdf) | Documento de pre-entrega (fuente: `preentrega.tex`; copia editable: `preentrega.md`) |
| [`docs/guia-terraform.md`](docs/guia-terraform.md) | **Empezá por acá si nunca usaste Terraform**: conceptos, cómo leer el código y por dónde arrancar |
| [`docs/decisiones.md`](docs/decisiones.md) | Por qué se eligió cada cosa (para responder en la defensa) |
| [`docs/presentacion.md`](docs/presentacion.md) | Guion de la presentación y de la demo |

## Cómo se opera

Todo cambio se hace editando `terraform/terraform.tfvars` y ejecutando `terraform apply`:

| Quiero... | Cambio en `terraform.tfvars` |
|---|---|
| Escalar un servicio | `replicas = { ui = 4, ... }` |
| Desplegar otra versión (o volver atrás) | `app_version = "1.1"` |
| Cambiar el tema visual de la tienda | `ui_theme = "green"` |
| Aislar un servicio comprometido | `quarantine = ["checkout"]` |

Nunca se toca el clúster a mano: si alguien lo hace, `terraform plan` lo detecta y
`terraform apply` lo corrige.

```bash
export KUBECONFIG=~/.kube/the-store.kubeconfig
kubectl get pods -n the-store -o wide      # estado de la aplicación
kubectl get svc,ingress,netpol -n the-store
kubectl logs -n the-store deploy/orders    # logs de un servicio
docker network inspect kind                # la red y las IPs de los nodos
```

## Licencia

El código de la aplicación (`the-store/`) pertenece a sus autores (proyecto
*retail-store-sample-app*, licencia MIT-0). El código Terraform y la documentación son parte
del TP Especial de Redes de Información del ITBA.
