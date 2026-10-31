# T04 — Terraform sobre los dos kind privados

`terraform/aplicacion` administra Kubernetes con los aliases `kind_a` y `kind_b`, con estado S3 independiente de `terraform/infra`. No tiene providers AWS/Helm, autenticación EKS ni recursos IAM. Cada módulo hijo recibe explícitamente su provider; T08 puede agregar los servicios sobre esta base.

## Preparar el entorno

Con credenciales vigentes del Lab, inicializar infra según T02/T03, revisar/aplicar su plan y esperar el bootstrap real. El apply de infra no espera que kind esté listo:

```bash
python3 scripts/verificar-computo.py --report .local/compute-report.json
python3 scripts/estado.py init aplicacion --bucket NOMBRE_DEL_BUCKET_DEL_GRUPO
terraform -chdir=terraform/aplicacion validate
```

La inicialización y validación de app no requieren las API Kubernetes. Tampoco las necesita `terraform -chdir=terraform/infra plan`: no hay providers Kubernetes ni dependencia del estado de app en esa raíz. **No usar la raíz histórica `terraform/` de EKS.**

## Abrir acceso y operar

```bash
python3 scripts/acceso.py run -- terraform -chdir=terraform/aplicacion plan -input=false
```

El comando se ejecuta después de abrir y verificar **ambos** túneles. Para revisar un plan y aplicarlo dentro de la misma sesión:

```bash
python3 scripts/acceso.py run -- bash
terraform -chdir=terraform/aplicacion plan -input=false -out=../../.local/app.tfplan
terraform -chdir=terraform/aplicacion apply ../../.local/app.tfplan
exit
```

Estos últimos tres comandos se ejecutan dentro de la shell abierta por el primero. `TF_VAR_access_manifest` identifica el acceso temporal; no escribirlo en tfvars. Al salir, finalizar el comando o interrumpirlo con Ctrl+C/SIGTERM, se cierran los procesos/sesiones SSM propios y se elimina el directorio temporal. Los planes contienen paths de esa sesión: si ya cerró, generar un plan nuevo con acceso nuevo. No reutilizar planes entre recreaciones de EC2/kind.

No se modifica `~/.kube/config`. Los kubeconfigs y el manifest son archivos 600 dentro de un directorio temporal 700 en `.local/`, ignorado por Git. No imprimirlos, subirlos ni activar logs de depuración del proveedor. El wrapper elimina variables `KUBE_*`, `KUBECONFIG` y detección in-cluster del entorno del comando para evitar destinos implícitos. No se leen ni copian claves del perfil AWS.

## Qué se comprueba

El acceso obtiene IDs desde el estado actual de infra y verifica EC2 running, privada, VPC/subred/IP/AZ y LabInstanceProfile. Recupera el kubeconfig y UID de `kube-system` del host usando SSM Run Command. Abre SSM Port Forwarding de `127.0.0.1:16443` hacia a:6443 y de `127.0.0.1:26443` hacia b:6443; no abre SSH ni puertos de API en los SG.

Para cada destino exige contexto `kind-the-store-a/b`, endpoint loopback acordado, CA y certificado/clave de cliente, TLS verificado, API Ready, UID coincidente con el recuperado por SSM y nombres de los dos nodos esperados. A y B deben tener instancias y UID distintos. Falla si un puerto está ocupado y no cierra procesos ajenos. Un lock local impide dos administradores en el mismo checkout; el bloqueo S3 sigue coordinando Terraform entre equipos.

`data.external.access` comprueba ambos destinos antes de configurar los providers y solo devuelve paths/contextos/UID. Para cubrir también `apply` de un plan guardado y operaciones con `-refresh=false`, el kubeconfig del provider usa un plugin local `ExecCredential`: valida nuevamente **ambos** accesos antes de devolver el certificado de cliente a client-go. El kubeconfig de validación conserva autenticación directa por certificado, evitando recursión. No usa `aws eks get-token`; el plugin no renueva certificados ni credenciales AWS. Certificados/claves nunca se pasan como variables, outputs o atributos de Terraform.

Esto comprueba disponibilidad antes de iniciar cada operación; una caída durante una operación ya iniciada puede dejar un apply parcial, que se resuelve restaurando acceso, revisando el plan y reintentando. Si el Lab expira, renovar credenciales localmente y abrir acceso nuevo. SIGKILL o apagar el equipo no permiten ejecutar limpieza: revisar procesos/sesiones propios y retirar el material temporal obsoleto antes de continuar; no borrar locks S3 ni cerrar sesiones ajenas.

## Prueba real reproducible

Con ambos kind listos y el estado de app vacío:

```bash
python3 scripts/probar-terraform-kind.py
```

El script rehúsa ejecutarse si app ya contiene recursos administrados. Crea un namespace `the-store-t04-probe` y ConfigMap `access-proof` por kind mediante Terraform, lee los destinos por API, actualiza ambos valores, exige convergencia y destruye los cuatro recursos. Usa `enable_access_probe=true`; por defecto es false y no se despliega ninguna aplicación T08.

Comprueba rechazo de identidad cruzada, segunda sesión local y túnel B caído. Con B caída intenta plan, apply guardado y destroy sin refresh, y exige que A conserve sus objetos/valores. Reabre ambos accesos para comprobar también B y completar destroy; verifica que ambas EC2 sigan running y que los planes/estado no contengan certificados ni claves. Ejecuta además el arnés T10 en modo bootstrap. Los reportes/planes/logs quedan privados en `.local/t04/`.

Si la prueba se interrumpe o falla después de crear probes, revisar el estado y retirarlos con ambos accesos disponibles antes de repetir o destruir infra:

```bash
python3 scripts/acceso.py run -- terraform -chdir=terraform/aplicacion destroy -input=false -var=enable_access_probe=true
```

Este destroy alcanza **todo el estado de aplicación**: cuando T08 esté implementada también retirará sus servicios. Luego revisar/aplicar destroy de infra y auditar AWS; conservar bucket/estado y recursos IAM del Lab. Nunca destruir EC2 antes de los objetos Kubernetes.

Referencias: [provider Kubernetes](https://registry.terraform.io/providers/hashicorp/kubernetes/3.4.0/docs), [plugins de credenciales client-go](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#client-go-credential-plugins), [data source external](https://registry.terraform.io/providers/hashicorp/external/2.4.2/docs/data-sources/external).

## Evidencia del 31/10/2026

- Infra recreada desde estado vacío: dos EC2 privadas y bootstrap/NodePort/Calico/repetición T03 aprobados; T10 bootstrap por ambas API también PASS.
- Ciclo real T04: cuatro altas (dos namespaces y dos ConfigMaps), lectura por API de cada identidad/valor, dos actualizaciones, plan convergente y cuatro bajas. Estado app vacío y ambas EC2 todavía running tras destroy.
- Identidad cruzada y segunda sesión del checkout rechazadas. Se cortó el túnel B: plan, apply de plan guardado y destroy con refresh desactivado fallaron. Al reabrir acceso, ambos ConfigMaps conservaban el valor anterior. El provider oculta stderr de ExecCredential en algunos errores; el wrapper vuelve a comprobar el acceso ante un comando fallido para explicar el motivo.
- Estado y JSON de planes comprobados contra los certificados/claves reales: no los contienen. Directorios privados temporales retirados y puertos locales libres al cerrar.
- SIGTERM real al wrapper durante un comando: hijo detenido, retorno 130, túneles y material temporal retirados. Plan infra sin túneles ni manifest válido: cero cambios.
- 34 tests Python, sintaxis, Terraform fmt/validate aprobados. La aplicación completa y sus datos siguen pendientes de T06–T09/T11.
- Red/EC2 conservadas temporalmente para ejecutar T05 por pedido del grupo; no se modificó IAM. El bucket de estado permanece retenido.
