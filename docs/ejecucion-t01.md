# T01 — Viabilidad y herramientas

Fecha: 31/10/2026. Ejecutar desde la raíz del repo:

```bash
python3 scripts/preflight.py --report .local/preflight.json
python3 -m unittest discover -s tests -p test_preflight.py -v
scripts/probar-kind.sh
# Sonda AWS temporal facturable, con limpieza automática:
python3 scripts/probar-ssm.py --create-probe
```

Preflight consulta AWS con el perfil configurado o `--profile nombre`; nunca crea recursos ni imprime credenciales o stderr de AWS. Salidas: 0 todo aprobado, 1 fallo local/contrato/respuesta incompatible, 2 comprobaciones AWS pendientes. `--offline` no certifica AWS. `--instance-id` permite revisar el agente SSM de una EC2 propia cuando exista en T03. Los reportes quedan ignorados por Git y con permisos 600.

## Sesión y cuenta

La primera sesión devolvió InvalidClientTokenId. El usuario renovó ~/.aws/credentials y STS autenticó correctamente. No se copiaron claves al repositorio ni a contenedores. Según el usuario la cuenta estaba vacía; las consultas confirmaron cero VPC con tag Project=the-store y ningún bucket con prefijo the-store-tfstate. Esto no equivale a un inventario completo de todos los servicios de la cuenta.

Consultas verificadas: LabInstanceProfile incluye LabRole; us-east-1a/b disponibles; t3.large es x86_64, tiene 8 GiB y al menos dos vCPU; existen opciones db.t3.micro con gp2 y Multi-AZ para MySQL y PostgreSQL; Redis 7.1 aparece disponible. Una opción anunciada por Describe no prueba que el Lab autorice crearla: las creaciones se comprueban en sus tareas y no se modifican los roles del Lab.

Restricciones observadas: AccessDeniedException en Service Quotas y pricing:GetProducts. No se interpreta esa denegación como ausencia de cuota ni se intenta ampliar permisos. Una consulta PostgreSQL sin límite de páginas agotó el tiempo; la consulta acotada confirmó opciones y el preflight ahora limita sus resultados.

## Combinación elegida

`config/herramientas.json` fija kind 0.33.0, imagen kindest/node Kubernetes 1.37.0 por digest y Calico 3.33.0. La [release oficial de kind](https://github.com/kubernetes-sigs/kind/releases/tag/v0.33.0) publica ese digest y los [requisitos de Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements) incluyen Kubernetes 1.37. El host tiene Terraform 1.16.1, Docker 29.6.2, kind 0.33.0 y kubectl 1.37.2. EC2 usará Linux x86_64 con kernel compatible; la AMI concreta se fija en T03.

El instalador del plugin SSM está en `scripts/instalar-plugin-ssm.sh`, y usa el [paquete oficial para Ubuntu](https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-debian-and-ubuntu.html), en ~/.local/share y ~/.local/bin. No cambia archivos de shell ni requiere sudo. El acceso a las dos EC2 privadas se valida en T03/T04; la sonda temporal T01 ya comprobó una sesión real, como se detalla al final.

**Resultado local: PASS.** Dos nodos Ready, respuesta HTTP por NodePort, conexión de ambos clientes antes de la política, permiso del cliente autorizado, bloqueo del otro y recuperación tras retirar la política. Se comprobó además que al terminar solo permanece el clúster previo `redes`.

La prueba kind es aislada, usa un kubeconfig temporal y elimina solo su clúster `t01-probe-*`; no modifica el clúster `redes` existente. Verifica entrada por NodePort y conectividad antes/después de una NetworkPolicy, incluido un control positivo de la sonda que luego se bloquea. El pool Calico debe coincidir con 10.244.0.0/16; no alcanza con modificar un valor que sigue comentado en el manifiesto.

Las imágenes Calico se descargan del mirror oficial Docker Hub y se cargan a ambos nodos desde un archivo amd64. Esto evita pulls lentos de Quay y el error de digest al importar índices multi-arquitectura incompletos del image store de Docker. La prueba requiere `docker image save --platform` (API 1.48+) y espera la propagación inicial de NodePort.

Se detectó `fsnotify watcher init: too many open files` con límites del host 128 instancias inotify y 65536 watches. Se elevaron durante la prueba a 1024 y 524288, sin hacer persistente el cambio ni tocar otros clústeres. El bootstrap de T03 debe contemplar esos mínimos; si no están disponibles, la prueba debe informar el requisito en lugar de confundirlo con fallo de red. El script ahora comprueba esos límites antes de crear el clúster.

## Capacidad y presupuesto

Requests base por EC2: 2 × (512 + 256 + 512 + 512 + 256) = 4096 MiB. UI 2→4 agrega 1024 MiB; un rollout agrega memoria transitoria. Candidato inicial: t3.large de 8 GiB, sujeto al permiso real y la prueba de carga de T08. Los dos nodos kind no duplican la memoria de la EC2. Vigilar créditos CPU de instancias burstable.

Estimación orientativa para planificar sesiones, no cotización ni saldo de Academy: reservar **USD 0,50–0,80/h para el POC completo**, incluyendo cómputo, datos Multi-AZ, ALB, red y almacenamiento; varía por motores/clases, tráfico, LCU y créditos CPU. No reutilizar el USD 0,30/h del README EKS antiguo. Validar las tarifas de us-east-1 y el saldo visible en Academy antes de dejar el entorno encendido.

Para la prueba T02 se presupuestan aproximadamente **USD 0,12/h de red**: 2 NAT × 0,045 + 2 IPv4 × 0,005 + 2 ENI de endpoint × 0,01, más datos/operaciones/estado S3. Son supuestos explícitos: la [página VPC](https://aws.amazon.com/vpc/pricing/) ilustra la tarifa NAT de 0,045 en Ohio y publica IPv4; [PrivateLink](https://aws.amazon.com/privatelink/pricing/) ilustra 0,01/ENI-h. La traslación de NAT a Virginia es una aproximación a confirmar en el [calculador oficial](https://calculator.aws/), ya que el Lab deniega la API de precios. Endpoint/NAT pueden facturar horas parciales como horas completas. Destruir la red de prueba al terminar; conservar únicamente el bucket y sus estados/versiones.

## Alcance de la evidencia

La base local y las consultas anteriores son ejecutables y repetibles. **La sonda AWS pasó:** lanzamiento real de una t3.large con LabInstanceProfile (PassRole efectivo), agente Online y sesión SSM con port forwarding que recibió el banner SSH remoto. El SG no tenía reglas de ingreso; el puerto 22 se alcanzó únicamente por el túnel autenticado. Se terminaron la instancia y su volumen raíz, y se eliminó el SG propio.

La sonda usa temporalmente una subred pública de la VPC default existente y salida HTTPS, sin modificar esa VPC ni sus tablas/SG previos. Esto valida los permisos de sesión; el diseño definitivo sigue siendo dos EC2 **privadas** y su conectividad se verifica en T03/T04. Guarda AMI/IDs propios en .local/t01-ssm-*/resources.json y siempre intenta limpiar; si la limpieza falla, revisar ese registro antes de repetir.

El plugin SSM 1.2.896.0 se instaló y ejecutó correctamente. La descarga lenta se resolvió reanudando el paquete de la fuente oficial; se verificó el ETag completo y el instalador ahora fija versión/SHA256 y reanuda intentos.

Quedan para comprobación operativa en sus tareas: capacidad simultánea de las dos EC2 (la API de cuotas sigue denegada), memoria bajo la aplicación, conectividad/IAM desde pods y configuraciones finales RDS/Redis. El preflight no les asigna PASS por haber leído metadatos. El saldo de Academy no está disponible mediante las APIs consultadas.
