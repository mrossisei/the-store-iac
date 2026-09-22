# Presentación final: estructura y guion de la demo

Formato: 30 minutos, remoto, con demo en vivo. La cátedra evalúa que se haya
implementado **exactamente** lo propuesto en la pre-entrega, así que la
presentación sigue su misma estructura y la demo recorre sus cuatro casos de
uso. Entregables además de la exposición: la presentación (PPT/PDF), el
repositorio con el código y el how-to (`README.md`).

## Antes de la presentación

- [ ] **T-60 min:** `terraform apply` con los valores base de
      `terraform.tfvars` (ui = 2, node_count = 2, app_version = "1.0",
      quarantine = []). Tarda ~25 min; dejar margen.
- [ ] `./verificar.sh` en verde. Abrir la tienda en el navegador y hacer una
      compra de prueba.
- [ ] `$(terraform output -raw kubeconfig_command)` en la terminal que se va a
      compartir; `kubectl get nodes` responde.
- [ ] Terminal con fuente grande, tema claro, dos pestañas: una para
      Terraform y otra para `kubectl`/`curl`.
- [ ] Consola de AWS abierta en VPC > Subnets y en EKS (para mostrar que lo
      que creó Terraform es real).
- [ ] Plan B: capturas de pantalla y un video corto de cada caso de uso
      grabados en un ensayo, por si AWS o la conexión fallan.
- [ ] Repartir quién habla en cada parte; los tres tienen que poder responder
      preguntas sobre cualquier archivo.
- [ ] Al terminar: `terraform destroy` (no dejarlo prendido).

## Estructura de las diapositivas (≈ 15)

1. **Portada.** Título, materia, integrantes.
2. **Problemática.** Infraestructura a mano: snowflake servers, sin registro,
   sin reproducibilidad. Qué es `local.sh` y qué no puede hacer (imperativo,
   sin estado, sin plan, sin drift).
3. **The Store.** Los cinco microservicios, lenguajes y persistencias
   (tabla). Es una tienda web: catálogo, carrito, checkout, órdenes.
4. **Infraestructura como Código.** Declarativo vs imperativo, el ciclo
   `init/plan/apply/destroy`, el estado. Por qué Terraform (una frase sobre
   Pulumi/OpenTofu/Ansible).
5. **Arquitectura (el diagrama).** Dedicarle tiempo: VPC 10.0.0.0/16, zonas,
   subredes públicas /24, privadas /20 y de datos /24, IGW, NAT, VPC
   Endpoints, tablas de ruteo, EKS con nodos AL2023, ALB → pods, bases
   administradas, protocolos y puertos.
6. **Camino de un pedido.** Navegador → IGW → ALB (L7, :80) → pod de la UI
   (:8080, IP del pod como target) → backends por DNS interno (Service, DNAT
   172.20.x.x → pod :8080) → RDS/ElastiCache (3306/5432/6379, security group)
   y DynamoDB y SQS (443 por VPC Endpoints), con IAM.
7. **Seguridad de red.** Security group de datos (sólo desde los nodos),
   NetworkPolicies (deny por defecto, UI sólo desde el ALB, backends sólo
   desde la app, cuarentena), nada con IP pública salvo el ALB y el NAT.
8. **El código.** Árbol de archivos, los cinco módulos y cómo se conectan
   (el grafo de `guia-terraform.md`), variables en un solo `tfvars`, estado
   en S3 con bloqueo.
9. **Decisiones.** VPC a mano vs módulo; módulo de EKS; ALB con el AWS Load
   Balancer Controller vs nginx+NLB; NAT + endpoints Gateway vs sólo
   endpoints; rol de nodos vs IRSA; kind primero y por qué se dejó.
10. **Demo: caso 1** (drift, plan, apply).
11. **Demo: caso 2** (escalamiento de réplicas y nodos).
12. **Demo: caso 3** (versión nueva, rolling update, rollback).
13. **Demo: caso 4** (cuarentena de checkout).
14. **Destroy** (arrancarlo en vivo, mostrar el plan de destrucción; termina
    después de la presentación).
15. **Conclusiones y mejoras.** Qué se ganó respecto de `local.sh`; qué
    faltaría para producción (IRSA por microservicio, TLS, CI, observabilidad,
    autoescalado).

## Guion de la demo (≈ 15 minutos)

El entorno ya está creado. Cada caso: mostrar el cambio en `terraform.tfvars`,
`terraform plan`, `terraform apply`, y la evidencia.

### Caso 1: reproducibilidad y drift (3 min)

```bash
terraform output                       # url, redes, endpoints
terraform state list | wc -l           # cuántos recursos administra
kubectl get nodes -o wide              # 2 nodos Ready, IPs privadas 10.0.x.x
kubectl get pods -n the-store -o wide  # 10 pods (2 réplicas por servicio, repartidas en las zonas)
```

Abrir la tienda por la URL del output. Después el drift:

```bash
kubectl scale deployment ui -n the-store --replicas=1     # "alguien tocó algo a mano"
terraform plan                                            # detecta: replicas 1 -> 2
terraform apply -auto-approve                             # lo corrige
kubectl get pods -n the-store                             # ui vuelve a 2
```

Mensaje: Terraform sabe cómo debería estar todo y lo devuelve a ese estado.
La creación completa ya se hizo antes (mostrar la salida guardada del `apply`
inicial con el tiempo: "Apply complete! Resources: N added").

### Caso 2: escalamiento (4 min, el apply del nodo tarda ~3)

Editar `terraform.tfvars`: `ui = 4`, `node_count = 3`.

```bash
terraform plan            # 2 cambios: Deployment ui (replicas 2->4) y grupo de nodos (2->3)
terraform apply -auto-approve
kubectl get nodes -w      # aparece el tercer nodo (mientras, seguir hablando)
kubectl get pods -n the-store -o wide   # 4 pods de ui repartidos en los nodos
```

Mostrar en la consola de AWS la tercera instancia EC2 en una subred privada.
Mensaje: un archivo, un plan, y escala la aplicación y la infraestructura.
Volver a `ui = 2`, `node_count = 2` (se puede aplicar después, o al final).

### Caso 3: versión nueva y rollback (4 min)

Antes de la presentación dejar preparado un cambio visible en la UI (por
ejemplo, un texto en la página principal en `the-store/src/ui`). Editar
`terraform.tfvars`: `app_version = "1.1"`.

```bash
terraform plan            # rebuild de las 5 imágenes + 5 Deployments cambian de imagen
terraform apply -auto-approve
kubectl rollout status deployment/ui -n the-store     # pods nuevos reemplazan a los viejos de a uno
```

Recargar la tienda: se ve el cambio; mientras tanto nunca dejó de responder
(tener un `watch -n1 curl -s -o /dev/null -w '%{http_code}\n' $URL` en la
otra pestaña). Rollback: `app_version = "1.0"`, `apply`, la tienda vuelve a la
versión anterior. Mostrar en ECR que existen los tags 1.0 y 1.1.

### Caso 4: incidente de seguridad (3 min)

Editar `terraform.tfvars`: `quarantine = ["checkout"]`.

```bash
terraform plan            # 1 cambio: etiqueta tier de checkout -> cuarentena
terraform apply -auto-approve
kubectl exec -n the-store deploy/ui -- curl -s -m 3 http://checkout/health ; echo "exit $?"    # 28 = timeout
kubectl exec -n the-store deploy/checkout -- curl -s -m 3 http://orders/  ; echo "exit $?"     # 28 = timeout
```

En la tienda: el catálogo y el carrito funcionan; al pasar al checkout la UI
muestra error. Mensaje: se contuvo el incidente sin apagar el servicio ni
tocar el resto; el `plan` mostró exactamente qué se iba a cambiar. Levantar la
cuarentena: `quarantine = []`, `apply`.

### Cierre: destroy (1 min)

```bash
terraform plan -destroy | tail -5     # "Plan: 0 to add, 0 to change, N to destroy"
terraform destroy -auto-approve       # arrancarlo y seguir con las conclusiones
```

## Preguntas que pueden hacer (y la respuesta corta)

- **¿Por qué las subredes privadas son /20 y las públicas /24?** Los pods
  toman IPs de la subred (VPC CNI); las públicas sólo alojan el ALB y el NAT.
- **¿Por qué un NAT Gateway por zona?** Para que la caída de una zona no
  deje sin salida a Internet a la otra: cada subred privada rutea al NAT de su
  zona.
- **¿Cómo llega el tráfico del ALB a los pods?** El AWS Load Balancer
  Controller registra las IPs de los pods de la UI como targets del ALB
  (`target-type: ip`); el ALB termina HTTP y manda cada pedido al puerto 8080
  del pod, sin NodePort ni proxy intermedio.
- **¿Por qué el controlador necesita un rol IAM?** Porque crea recursos de
  AWS (ALB, target groups, security groups) desde adentro del clúster. Lo
  asume por IRSA: un token de la service account firmado por el clúster que
  STS cambia por credenciales.
- **¿Las bases están en Internet?** No: IP privada, sin `publicly_accessible`,
  security group que sólo acepta al security group de los nodos.
- **¿Por qué DynamoDB y SQS no tienen security group?** Son servicios
  regionales fuera de la VPC; el acceso se controla con IAM. A DynamoDB se
  llega por un VPC Endpoint de tipo Gateway (ruta dentro de AWS, sin costo);
  a SQS por uno de tipo Interface, que sí tiene security group (443 desde la
  VPC).
- **¿Dónde están las contraseñas?** Las genera Terraform (`random_password`),
  viven en el estado (bucket privado, versionado) y llegan al pod como
  variable de entorno marcada sensible.
- **¿Qué pasa si dos personas hacen `apply` a la vez?** El backend S3 bloquea
  el estado (`use_lockfile`); el segundo espera o falla con "state locked".
- **¿Por qué no usaron el módulo de VPC?** Para que la red sea explícita y
  explicable; los módulos de EKS e IAM sí, porque IAM no es el foco.
- **¿Por qué no sacaron el NAT y usaron sólo VPC Endpoints?** Harían falta
  endpoints Interface también para ECR (×2), EC2, STS y ELB, y replicar en ECR
  la imagen del controlador, que vive en el ECR público. Se usan endpoints sólo
  para lo que usa la aplicación: S3 y DynamoDB (Gateway, gratis) y SQS
  (Interface).
- **¿Cuánto cuesta?** ~USD 0,30/h. Se crea por sesión y se destruye.
- **¿Qué cambiaría para producción?** NAT por zona, RDS Multi-AZ con
  backups, IRSA por microservicio, TLS con dominio propio, autoescalado,
  observabilidad, CI que corra `plan` en cada pull request.
