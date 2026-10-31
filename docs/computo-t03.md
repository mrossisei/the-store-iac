# T03 — Dos EC2 privadas con kind y Calico

La raíz terraform/infra agrega modules/computo: una t3.large en cada subred privada a/b, sin IP pública ni ingreso SSH/API, con el SG de aplicación de T02 y LabInstanceProfile existente. No hay recursos IAM/EKS nuevos. Cada host tiene disco raíz gp3 de 40 GiB, cifrado y con delete_on_termination. El límite gp2 del plan corresponde a RDS; este disco no es una base RDS.

config/herramientas.json fija la AMI Amazon Linux 2023 x86_64 para us-east-1, kind, Kubernetes, Calico y checksums. La AMI se consultó por /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64, se verificó propietario Amazon (137112412989), arquitectura x86_64 y raíz EBS; el ID se fijó en el archivo para no actualizar hosts por una consulta latest en cada plan. Docker/AWS CLI se instalan del snapshot de repositorios de esa AMI; sus versiones efectivas quedan en los diagnósticos del host. Para cambiar AMI o bootstrap se revisa el reemplazo en el plan.

## Crear y comprobar

Con backend T02 inicializado y credenciales vigentes:

```bash
terraform -chdir=terraform/infra init
terraform -chdir=terraform/infra plan -out=../../.local/t03.tfplan
terraform -chdir=terraform/infra apply ../../.local/t03.tfplan
python3 scripts/verificar-computo.py --reboot --report .local/t03-report.json
jq '{status,reboot_tested,clusters,failures}' .local/t03-report.json
python3 scripts/probar-apis.py
terraform -chdir=terraform/infra plan -detailed-exitcode
```

El apply espera EC2, **no** da por terminado el bootstrap. El verificador espera SSM Online, comprueba cada invocación de Run Command (Status y ResponseCode), espera readiness y ejecuta pruebas en cada host. Los dos kind deben tener diferentes UID de kube-system. Los archivos de diagnóstico son privados y quedan en .local/. No se imprimen kubeconfigs ni credenciales de la cuenta.

compute es un mapa a/b con instance_id, private_ip, availability_zone y cluster_name. Este output permite agregar ALB/targets en T05; no contiene certificados. La API escucha exclusivamente en 127.0.0.1:6443 de cada host y el kubeconfig queda en /var/lib/the-store/kubeconfig con permisos 600. Los túneles/kubeconfigs del operador y los providers Terraform son T04; T03 usa SSM Run Command para pruebas locales al host.

## Bootstrap y repetición

cloud-init escribe los archivos en /opt/the-store y habilita the-store-kind.service. El servicio:

1. Instala/activa Docker, AWS CLI y agente SSM. Incluye /usr/sbin y /sbin en PATH para sysctl/modprobe. Configura ip_forward y límites inotify persistentes (1024 instancias, 524288 watches).
2. Descarga kind/kubectl por versión y verifica SHA256. Crea control-plane + worker, kindnet deshabilitado, CIDR pod/Service del contrato y mapeo host:8080→containerPort/NodePort:30080. El módulo espera **toda** la red, incluidos NAT/rutas, antes de lanzar las EC2.
3. Verifica el manifiesto Calico por SHA256, ajusta el pool a la configuración compartida, usa el mirror oficial Docker Hub y precarga imágenes amd64 en ambos nodos. Soporta Docker con image store clásico y con containerd.
4. Espera Calico, controllers, nodos y CoreDNS; recién entonces escribe status.json PASS. Un fallo deja servicio no activo, bootstrap-error y journal; no reutiliza un PASS antiguo.

En otra ejecución no elimina el clúster. Comprueba el hash de configuración, recupera los mismos contenedores y reaplica el mismo manifiesto. Si encuentra una configuración diferente o un clúster incompleto, falla para revisar el reemplazo; no borra pods/datos en silencio. En un reinicio, systemd vuelve a preparar y los contenedores tienen restart=always. Se conserva su almacenamiento en el disco raíz durante reboot; destruir/reemplazar la EC2 sí elimina el kind y ese volumen.

La política IMDS exige v2 y fija hop limit 3 por las capas EC2→kind→pod. Esto es una decisión explícita que T08/T10 deben comprobar desde Cart/Orders; SSM en el host no demuestra acceso IAM desde pods. No hay claves personales dentro de user-data ni se crean roles nuevos.

## Pruebas reales de T03

smoke.sh crea un namespace único en **el kind real**, espera tres pods de sonda y verifica que ambos clientes lleguen al servidor antes del aislamiento. Publica NodePort 30080 y obtiene respuesta a través del puerto 8080 del host; luego permite un cliente y exige timeout de wget del otro. Rechaza errores de herramienta/exec distintos del timeout comprobado. Al retirar la policy exige recuperación y elimina el namespace incluso si falla. Ejecutar antes de T08: si ese NodePort está ocupado por la aplicación, la sonda debe fallar.

probar-apis.py abre túneles temporales con el plugin SSM, copia kubeconfigs únicamente a un directorio privado temporal y verifica TLS con la CA/certificado original (sin insecure-skip-tls-verify). Ejecuta el modo bootstrap de T10 sobre las dos API; después exige FAIL al repetir el mismo contexto y al usar una API inaccesible con contexto válido. Cierra sus procesos/sesiones y elimina kubeconfigs temporales. No crea providers ni objetos de aplicación de T04. Requiere libres los puertos locales 16443/26443; no cierra túneles ajenos.

El verificador ejecuta esa prueba, repite systemctl restart the-store-kind y exige los mismos contenedores y UID de clúster. Con --reboot reinicia ambas EC2, exige boot_id diferente y los mismos UID de clúster/nodos/contenedores, y repite el smoke. No se toma una respuesta previa al reboot como evidencia de recuperación.

Esto prueba CNI, DNS de los pods y el mapeo local de entrada; el tráfico real ALB→EC2 se comprueba al agregar T05/T08, y ECR/datos/IAM de aplicación en sus tareas. La falta de EC2 pública se valida mediante DescribeInstances, además de la configuración Terraform.

## Diagnóstico y limpieza

Desde una sesión SSM en el host:

```bash
systemctl status the-store-kind --no-pager
journalctl -u the-store-kind -n 100 --no-pager
cat /var/lib/the-store/bootstrap-error
cat /var/lib/the-store/status.json
sudo /opt/the-store/prepare.sh
sudo /opt/the-store/smoke.sh
```

No eliminar contenedores de otros clústeres, modificar LabRole ni desactivar TLS para resolver fallos. Los scripts no cambian el kubeconfig global del operador.

Al finalizar las pruebas T03 se revisa y aplica un plan de destroy **de infra**, se auditan IDs/tags de EC2/EBS/ENI/NAT/EIP/endpoints/VPC y se conserva el bucket S3. No ejecutar destroy del bootstrap. Para continuar T04/T05 recrear infra con apply y esperar el verificador.

Referencias de implementación: [kind quick start](https://kind.sigs.k8s.io/docs/user/quick-start/), [problemas conocidos de kind](https://kind.sigs.k8s.io/docs/user/known-issues/), [Docker en AL2023](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-docker.html), [estado por invocación SSM](https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_GetCommandInvocation.html).

## Evidencia del 31/10/2026

- Dos t3.large simultáneas, una en us-east-1a y otra en us-east-1b, sin IP pública, con perfil/SG esperados e IMDSv2 requerido. Capacidad efectiva observada: aproximadamente 8.007.500 KiB de RAM por host.
- Se recrearon ambas EC2 para probar el user-data corregido desde cero. Docker 25.0.14 y AWS CLI 2.38.0 del snapshot AL2023, kind 0.33.0, Kubernetes 1.37.0 y Calico 3.33.0 operativos; dos nodos Ready y CoreDNS/Calico saludables por kind.
- Smoke real en ambos hosts: HTTP por hostPort→NodePort, DNS de Service y SQS con IP privada de cada AZ, clientes permitidos antes de la policy, denegación por timeout y recuperación posterior. Namespaces de prueba eliminados.
- Segunda preparación: mismos contenedores y UID de clúster. Reboot real de ambas EC2: boot_id cambia; UID de clúster/nodos y contenedores permanecen; smoke repetido aprobado.
- T10 bootstrap ejecutado desde el operador sobre las dos API privadas por SSM y TLS validado. Reporte correcto PASS; controles de contextos duplicados y API inaccesible producen los FAIL esperados. Sesiones cerradas y kubeconfigs temporales eliminados.
- Plan de infraestructura sin cambios. Tests locales: 27 Python y cuatro Terraform (tres infra + uno bootstrap), fmt/validate y sintaxis Bash/Python/JavaScript aprobados. Las pruebas de app/ALB/datos permanecen pendientes de sus tareas.
- Limpieza: 44 recursos de infra eliminados. Auditoría por IDs: las cuatro instancias de ambas ejecuciones terminadas y todos sus EBS eliminados; sin VPC/ENI/SG/subredes/rutas/endpoints/EIP, NAT eliminados y estado infra vacío. Bucket/versiones de S3 y estado privado de bootstrap conservados.
