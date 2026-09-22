# The Store con Terraform — Infraestructura como Código

**TP Especial · Redes de Información · ITBA · 2C 2026 · Grupo NN**

Este repositorio despliega la tienda **The Store** (cinco microservicios) sobre un clúster de
Kubernetes, con **toda la infraestructura declarada en Terraform**: la red y su
direccionamiento, el clúster, el punto de entrada HTTP, las bases de datos, los microservicios
y las reglas de segmentación de red.

```bash
cd terraform
terraform init      # descarga los providers (una sola vez)
terraform plan      # muestra qué se va a crear
terraform apply     # crea todo (~15 min la primera vez)
```

Después de `apply`, la tienda queda en **http://the-store.localhost**.
Para borrar todo: `terraform destroy`.

![Arquitectura](docs/img/arquitectura.png)

## Requisitos

| Herramienta | Versión | Para qué |
|---|---|---|
| Docker | ≥ 24 | Los nodos del clúster son contenedores |
| Terraform | ≥ 1.10 | La herramienta de IaC |
| kind | ≥ 0.29 | Sólo para cargar las imágenes en los nodos |
| kubectl | 1.34–1.36 | Opcional, para inspeccionar el clúster |

Se necesitan además los puertos 80 y 443 libres, unos 15 GB de disco y 8 GB de RAM. En Linux
conviene subir los límites de inotify una vez:

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

the-store/               # código fuente de la aplicación (provisto por la cátedra)
docs/                    # pre-entrega, decisiones, guía de Terraform, diagrama
```

## Documentación

| Archivo | Contenido |
|---|---|
| [`docs/preentrega.pdf`](docs/preentrega.pdf) | Documento de pre-entrega (fuente: `preentrega.tex` y `preentrega.md`) |
| [`docs/guia-terraform.md`](docs/guia-terraform.md) | **Empezá por acá si nunca usaste Terraform**: conceptos, cómo leer el código y por dónde arrancar |
| [`docs/decisiones.md`](docs/decisiones.md) | Por qué se eligió cada cosa (para responder en la defensa) |
| [`docs/presentacion.md`](docs/presentacion.md) | Guion de la presentación y de la demo |

## Comandos útiles

```bash
export KUBECONFIG=~/.kube/the-store.kubeconfig

kubectl get pods -n the-store -o wide      # estado de la aplicación
kubectl get svc,ingress,netpol -n the-store
kubectl logs -n the-store deploy/orders    # logs de un servicio
docker network inspect kind                # la red y las IPs de los nodos
```

Para cambiar algo (réplicas, cantidad de nodos, versión, tema visual) se edita
`terraform/terraform.tfvars` y se ejecuta `terraform apply`. Nunca se toca el clúster a mano:
si alguien lo hace, `terraform plan` lo detecta y `terraform apply` lo corrige.

## Licencia

El código de la aplicación (`the-store/`) pertenece a sus autores (proyecto
*retail-store-sample-app*, licencia MIT-0). El código Terraform y la documentación son parte
del TP Especial de Redes de Información del ITBA.
