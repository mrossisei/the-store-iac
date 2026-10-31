# T05 — ALB público directo a las EC2 privadas

`terraform/modules/alb` crea un ALB público IPv4 en las dos subredes públicas, un listener HTTP/80 y un target group HTTP de tipo `instance` en el puerto 8080. Registra las dos EC2 mediante el mapa `a/b` de cómputo. Los SG siguen perteneciendo a red: ingreso público TCP/80 al ALB, salida TCP/8080 al SG EC2 y entrada EC2:8080 solo desde el SG ALB.

El recorrido es ALB:80 → EC2 privada:8080 → control plane kind:30080 → Service NodePort:30080 → pod UI:8080. No agrega roles, SSH, nginx, Helm ni AWS LBC. El ALB pertenece al estado AWS de `terraform/infra`; planear o destruir esa raíz no necesita túneles/API Kubernetes. Para destruir, retirar primero los recursos del estado de aplicación mientras existen ambos kind.

## Aplicar y consultar

Con backend S3 y credenciales del Lab configurados:

```bash
terraform -chdir=terraform/infra init
terraform -chdir=terraform/infra plan -out=../../.local/infra.tfplan
terraform -chdir=terraform/infra apply ../../.local/infra.tfplan
terraform -chdir=terraform/infra output -raw url
terraform -chdir=terraform/infra output -json load_balancer
```

Sobre una infraestructura T03 existente, el plan de T05 agrega cinco recursos: ALB, target group, listener y dos attachments. No reemplaza EC2 ni cambia red/IAM. Desde estado vacío crea también los recursos T02/T03 y debe esperarse su bootstrap.

`url` proviene de `aws_lb.this.dns_name`. `load_balancer` contiene `arn`, `dns_name`, `listener_arn`, `target_group_arn` y `target_ids` por a/b; `network` y `compute` mantienen sus contratos.

El health check usa HTTP al `traffic-port` con ruta `/actuator/health/readiness` y acepta exclusivamente 200; intervalo 15 s, timeout 5 s y dos éxitos/fallos consecutivos. Una redirección o una respuesta genérica en `/` no demuestra readiness. T08 debe publicar ese endpoint de la UI en 8080 y su Service en NodePort 30080. Los targets sin UI pueden quedar unhealthy y el ALB puede responder errores; tener un DNS público no certifica que la tienda esté desplegada. El healthy de la UI completa se comprueba en T11.

## Prueba real de red y balanceo

Antes de desplegar T08, con kind listos y NodePort 30080 libre en ambos:

```bash
python3 scripts/verificar-computo.py --report .local/compute-report.json
python3 scripts/probar-alb.py
```

La sonda contrasta por API AWS los recursos actuales: ALB activo/público, subredes, VPC/SG, listener, target group, health check y los dos IDs/puertos. Rechaza ingreso público a EC2, SSH o salida amplia del ALB. Obtiene acceso autenticado con el administrador SSM de T04 y comprueba que el NodePort no pertenezca ya a la aplicación.

En cada kind crea un namespace único con Deployment BusyBox HTTP y Service NodePort. El endpoint de readiness devuelve 200 y `/` identifica clúster y ejecución. Espera ambos targets healthy y exige respuestas HTTP públicas desde A y B. Escala únicamente la sonda B a cero, espera B unhealthy/A healthy y exige respuestas por A. Recupera B, vuelve a comprobar ambos healthy y tráfico a los dos. Finalmente elimina solo los namespaces cuyos UID creó, espera su eliminación, cierra acceso y exige ambos targets unhealthy sin las sondas.

El reporte y manifiestos quedan en `.local/t05/`, ignorados por Git. La prueba no aplica recursos de la tienda ni escribe en el estado de aplicación. Los namespaces de sonda se retiran también ante fallo o interrupción normal; si se perdió acceso, revisar los nombres indicados en los manifiestos y comprobar la limpieza antes de destruir EC2. No ejecutar esta sonda sobre T08: el NodePort ocupado provoca un rechazo deliberado.

## Retirar el entorno de pruebas

Con app vacía y sondas retiradas, revisar y aplicar un plan de destroy de **infra**, conservar el bucket y auditar EC2/EBS/ALB/target groups/VPC/ENI/NAT/EIP/endpoints/SG. No ejecutar destroy de bootstrap. Reaplicar infra recrea los hosts/kind y cambia sus identidades: abrir acceso nuevo y generar planes de app nuevos.

Referencias: [health checks ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html), [target groups ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html), [provider AWS target group](https://registry.terraform.io/providers/hashicorp/aws/6.66.0/docs/resources/lb_target_group).

## Evidencia del 31/10/2026

- Plan real: cinco altas exclusivamente en `module.alb`; red y ambas EC2 existentes sin cambios. Apply completado y ALB activo en las dos subredes públicas. Listener/targets/health check/SG contrastados mediante AWS.
- Baseline de sonda: ambos targets healthy; doce peticiones HTTP públicas exitosas, seis respuestas identificadas de A y seis de B.
- Fallo de B: se escaló su Deployment de sonda a cero, se observó A healthy/B unhealthy y doce respuestas HTTP exitosas de A.
- Recuperación: B vuelve a healthy; doce respuestas HTTP exitosas, ocho de A y cuatro de B. Las 36 respuestas identificaron además la ejecución actual de la sonda.
- Namespaces/NodePorts temporales eliminados en ambos kind, acceso SSM cerrado y targets nuevamente unhealthy al no existir UI/sondas. El estado app permaneció vacío; no se desplegaron servicios de T08.
- Plan infra convergente sin diferencias. 38 pruebas Python y cinco pruebas Terraform de infra aprobadas, junto con fmt/validate y sintaxis Python. La lectura de errores AWS distingue NotFound de denegaciones sin mostrar detalles privados de stderr.
- Limpieza revisada/aplicada: 49 recursos de infra eliminados. Auditoría final PASS por IDs: dos EC2 terminated, sus EBS eliminados, dos NAT deleted y EIP liberadas; sin ALB/listener/target group/VPC/ENI/SG/subredes/rutas/endpoints. Estados app/infra vacíos; sin manifests ni túneles locales. Bucket de estado y versiones conservados. No se declaró IAM ni se modificó LabRole.
