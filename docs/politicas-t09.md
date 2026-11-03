# T09 — Segmentación y cuarentena sin cambiar pods

El módulo `terraform/modules/politicas-kind` administra únicamente NetworkPolicies. La raíz lo instancia con los providers `kind_a`/`kind_b`, el namespace de cada módulo de aplicación y la misma lista `quarantine`. `enable_network_policies` vale `true` por defecto y solo tiene efecto con `enable_application = true`. No hay providers ni objetos de aplicación dentro del módulo hijo.

El namespace queda aislado por defecto para entrada y salida. Se habilitan exactamente cuatro caminos TCP/8080 entre pods del mismo namespace: UI→Catalog, UI→Carts, UI→Checkout y Checkout→Orders. Cada camino permite explícitamente ambos extremos. UI no puede llamar directamente a Orders y no existe permiso genérico por `tier=backend`.

Cada servicio activo tiene salida a destinos externos, excluyendo **ambos** CIDRs reales de pods y Services de `config/entorno.json`; esto evita un permiso alternativo hacia Checkout. La salida externa conserva acceso a MySQL/3306, PostgreSQL/5432, Redis/6379, IMDSv2/80 y APIs AWS/443, bajo las rutas y SG de infraestructura. Este módulo segmenta microservicios; no implementa una lista mínima de destinos externos por aplicación. DNS TCP/UDP53 se permite exclusivamente a pods `k8s-app=kube-dns` del namespace `kube-system`. Al cuarentenar un servicio se retiran todas sus aristas y su permiso externo/DNS. El deny permanece seleccionando sus pods sin cambiar etiquetas, PodTemplates ni réplicas.

Las políticas Kubernetes son aditivas: un deny vacío no revoca un allow existente. T08 debe retirar el legacy `network_policies.tf` y no debe haber policies externas que otorguen permisos alternativos. La sonda compara nombres y reglas completas contra la topología esperada y falla si encuentra permisos adicionales o modificados.

## NodePort, SNAT y probes

El SG de EC2 admite ALB→host8080; kind lo mapea a NodePort30080 y UI8080. La policy de UI permite TCP8080 desde fuera de las redes de pods/Services y desde las IP `/32` de los nodos. Las descubre con `data.kubernetes_nodes.cluster`: InternalIP y anotaciones Calico IPv4IPIPTunnelAddr/IPv4VXLANTunnelAddr. No usa un CIDR fijo del ALB como si su dirección sobreviviera a NAT. No permite todo el podCIDR de un nodo.

La medición local con Kubernetes1.37/Calico3.33 encontró que host127.0.0.1:18089→NodePort30080→UI8080 presentaba origen **10.244.237.192**, la IP de túnel Calico del nodo (InternalIP172.24.0.3). Esa dirección estaba dentro del pool de pods. El módulo contempla esas IP `/32` además del bloque externo; esto no implica que todos los caminos de host se filtren igual, porque hay excepciones del CNI para tráfico de nodos. La evidencia es `.local/t09/local-source.json`. La repetición local con UI en el worker confirmó el mismo origen de túnel del control plane. Retirar temporalmente los `/32` provocó timeout; restaurarlos recuperó HTTP. La fuente concreta del ALB en AWS requiere comprobación durante la campaña real.

Kubernetes permite tráfico del nodo local al pod; las sondas kubelet pueden seguir funcionando aun con cuarentena. La cuarentena representa aislamiento de red frente a otros workloads y destinos externos, no aislamiento del administrador/host. La prueba no interpreta un readiness fallido como prueba de bloqueo: verifica el proceso por loopback y usa IP de pod para el negativo. El `/health` actual de Checkout verifica el indicador de chaos, no Redis: estar Ready no demuestra conectividad a Redis. La sonda no depende de que ese health cambie ni de que el Service conserve endpoints; verifica Redis por protocolo y tráfico entrante por PodIP.

Referencias: [semántica aditiva y NAT de NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [excepción del nodo local en la API](https://kubernetes.io/docs/reference/kubernetes-api/networking/network-policy-v1/).

## Pruebas reproducibles

Mocks aislados, sin API ni necesidad de integrar primero T08:

```bash
python3 scripts/probar-politicas-terraform.py
python3 -m unittest discover -s tests -p test_politicas.py -v
```

Una vez aplicada y saludable la aplicación real, el operador compartido mantiene una sesión `scripts/acceso.py run` y proporciona su manifest temporal. La sonda también acepta `THE_STORE_ACCESS_MANIFEST` exportado por esa sesión. Nunca ejecutar accesos paralelos que intenten ocupar los mismos puertos. No contiene apply ni operaciones AWS:

```bash
umask 077
mkdir -p .local/t09
python3 scripts/probar-politicas.py --manifest "$THE_STORE_ACCESS_MANIFEST" \
  --phase baseline --evidence .local/t09/baseline.json
# El operador cambia quarantine=["checkout"], guarda/revisa/aplica el plan.
python3 scripts/validar-plan-politicas.py .local/t09/quarantine-plan.json
python3 scripts/probar-politicas.py --manifest "$THE_STORE_ACCESS_MANIFEST" \
  --phase quarantine --baseline .local/t09/baseline.json --evidence .local/t09/quarantine.json
# El operador revierte quarantine=[] y guarda/revisa/aplica otro plan.
python3 scripts/validar-plan-politicas.py .local/t09/restored-plan.json
python3 scripts/probar-politicas.py --manifest "$THE_STORE_ACCESS_MANIFEST" \
  --phase restored --baseline .local/t09/baseline.json --evidence .local/t09/restored.json
```

Los JSON de planes provienen de `terraform show -json PLAN` y contienen potencialmente secretos: guardar bajo `.local/`, modo600. El validador solo informa conteo y exige cambios administrados exclusivamente de tipo `kubernetes_network_policy_v1`, sin reemplazos. Un plan vacío no demuestra la transición. En Checkout se esperan cinco permisos retirados por clúster y cinco creados al revertir. Root T08 aún no integrado no se valida como si estuviera completo.

La sonda valida las identidades A/B mediante T04 y espera tres segundos para la programación asíncrona de Calico antes de probar tráfico. Verifica cada réplica, las cuatro aristas y negativos UI→Orders, Carts→Orders, Orders→Checkout y Checkout→Catalog/Carts. Utiliza PodIP/8080 y health HTTP200 para positivos; acepta como bloqueo únicamente curl28/HTTP000. Comprueba curl efectivo y proceso en loopback. Checkout usa Node ya presente en la imagen, con módulos estándar: Redis PING sin modificar datos, consulta DNS UDP/TCP con validación de respuesta y conexión TCP al puerto443 de una IP de example.com. Los destinos se resuelven y guardan en baseline; cuarentena usa exactamente las mismas IPs. Un error de DNS, credenciales, conexión rechazada, exec o herramienta faltante falla la prueba.

UI actúa como control durante las tres fases: resuelve Catalog y obtiene health200; abre sockets TCP a los mismos DNS/Redis/Internet con Bash/timeout existentes en AL2023. No instala nada ni envía payload a esos destinos externos. Estos controles detectan una caída del destino que pudiera confundirse con aislamiento. Se comparan UID, restartCount, imágenes y hash de PodTemplate de los cinco servicios entre fases y al principio/final de cada fase. No se crean sondas en pods, ni se cambian etiquetas, reinician deployments, consumen mensajes SQS o escriben en bases.

La compra UI y la comprobación de orden nueva se ejecutan con el arnés T10 antes/después de cuarentena, sin `--restart-for-persistence` en esta campaña, bajo coordinación del operador. Una comprobación TCP o de health no demuestra una compra completa.

## Estado de evidencia

Los cuatro tests mock y seis regresiones Python pasan. La campaña de un nodo aprobó las tres fases con 17 controles por fase; cuarentena/reversión retiraron y crearon únicamente cinco NetworkPolicies. La repetición con dos nodos aprobó las tres fases, también con 17 controles por fase, planes de cinco policies e identidades y PodTemplates estables. Las pruebas locales de Calico se ejecutan sobre servidores HTTP de ensayo con las cinco etiquetas de aplicación, usando el runtime de Checkout, no sobre la tienda real. El primer kind temporal de dos nodos se retiró tras agotar espacio; el segundo se probó con un nodo para limitar almacenamiento. Tras liberar espacio se repitió con dos nodos: UI/Catalog/Orders en worker y Carts/Checkout en control plane, forzando aristas y NodePort entre nodos. Esto no certifica el ALB ni la aplicación real.

**T09 no está cerrada.** Faltan los tres reportes de la aplicación real en ambos kind, planes reales de cuarentena/reversión solo policies, fuente de tráfico ALB/probes y compra real restablecida. El padre recupera el entorno del Lab; no se aplicó ni destruyó infraestructura compartida desde este worktree.
