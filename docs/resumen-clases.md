# Resumen de clases — Redes de Información (ITBA)
### Para el TP Especial "Gestión de Infraestructura por Código: Terraform" (The Store, K8s sobre Kind/Docker)

Documento de trabajo armado a partir de las 6 clases teóricas y las 6 prácticas (labs) de la cátedra. Pensado para dos cosas: (1) escribir el documento de pre-entrega (en especial el diagrama de arquitectura con CIDRs, redes, SO y protocolos) y (2) preparar el coloquio oral, donde van a preguntar de la materia dando por hecho que la conocés.

---

## Nota metodológica

El texto de los 12 PDF se extrajo con `pdftotext -layout`. Ninguno dio "casi sin texto extraíble": el más corto (Lab 6, BGP) tiene ~590 palabras y el más largo (Clase 2, cableado/switches/wifi) tiene ~3250. Igual, tené en cuenta:

- Son **diapositivas**, no apuntes en prosa: mucho contenido está en fotos, diagramas de topología, capturas de Packet Tracer y tablas-imagen que **no se extraen como texto**. Lo que sigue es fiel a lo que hay en texto; donde una diapositiva es "solo el diagrama" lo aviso.
- Clase 1 tiene muchas fotos (cables, satélites, mapas) sin texto asociado más que el título del slide.
- Clase 4 tiene un ejemplo de mapeo de labels MPLS cuyo diagrama ASCII salió parcialmente desordenado en la extracción (flechas y números mezclados); tomá los conceptos, no los números exactos de esa sección en particular.
- Los Labs 2 a 6 son guías de Packet Tracer: las topologías de red son imágenes; lo que se extrae son los enunciados y los comandos Cisco IOS, que es igualmente lo más citable para el TP.
- Todas las clases dicen "ITBA - RED - 2026" en el pie (2026 es el año de cursada actual), salvo los labs que traen su propio año de creación original (2019/2024/2025) — no es relevante, solo lo aclaro porque aparece así en el pie de página.

---

## Convenciones de notación de la cátedra (referencia rápida)

Para que el diagrama del TP "suene" como la cátedra:

- **Direcciones y máscaras**: la cátedra habla de **"dirección de red"**, **"máscara de red"/"máscara de subred"**, **"dirección de broadcast"**, **"rango asignable"**, **"gateway predeterminado"**, **"bloque"** (ej. "el bloque 192.168.10.0/24"). La palabra **"CIDR" no aparece ni una vez** en los 12 PDF — la cátedra no usa esa sigla, aunque usa exactamente la notación con barra (`/24`, `/20`, etc.) todo el tiempo, mezclada con máscara punteada en los labs (`255.255.255.192`). Para el TP podés usar "CIDR" con tranquilidad (es estándar de la industria), pero no esperes que el profesor use ese término — va a decir "bloque" o "rango".
- En ejemplos de WHOIS/LACNIC (Clase 3) el prefijo se escribe **recortado a los octetos significativos**: `190.188/15`, `209.13/16` (no ponen los octetos en cero). En CABASE (Clase 5) sí usan la forma completa: `200.0.17.0 /24` (con un espacio antes de la barra) e IPv6 con barra pegada: `2001:13c7:6001::/48`. Sabé que existen ambos estilos de notación.
- No usan la sigla **RFC 1918** en ningún lado, pero **todos los ejemplos prácticos** (Lab 1, Lab 4, Lab 5, el ejemplo de VPN de Clase 6) usan rangos privados: `192.168.x.x`, `10.x.x.x`, `172.16.x.x`. Es la convención de facto de toda la materia aunque nunca citen la RFC por número.
- **NAT**: la cátedra distingue **SNAT** (Source NAT) y **DNAT** (Destination NAT), y dentro de SNAT los 4 tipos clásicos: **Full Cone, IP Restricted, Port Restricted, Symmetric**. Ojo con un "falso amigo": en la Clase 5 (CABASE) **"PAT" significa "Punto de Agregación de Tráfico"**, no "Port Address Translation" — son cosas totalmente distintas, no lo confundas en el oral.
- **DMZ**: "Zona Desmilitarizada", literalmente descripta como "tierra de nadie". Reglas de tráfico con esta redacción exacta: *"Internet -> DMZ: controlado para servicios específicos"*, *"DMZ -> interno: muy restringido, mínimo acceso"*, *"interno -> DMZ: generalmente accesible al menos para management"*, *"Internet -> interno: bloqueado!"*.
- **VLAN**: "define dominio de Broadcast", y una frase clave para el TP: **"Permite tener IP overlapping"**.
- **VPN**: dos modos, **"Cliente a Sitio"** y **"Sitio a Sitio"** (así, con esas mayúsculas/guiones bajos conceptuales).
- **Ruteo**: "ruteo estático" vs "ruteo dinámico"; dentro de dinámico, **"estado de enlace"** (link-state), **"vector distancia"** (distance-vector) y **"path vector"**. BGP es "path vector". No usan el término "distance-vector" en inglés, siempre en español.
- **Switch vs Router**: la cátedra remarca que un **Switch Capa 3 no tiene puertos WAN** y que un Router sí soporta protocolos como PPP/Frame Relay que el switch L3 no soporta.
- El **MTU no se menciona en ningún PDF** (ni la palabra ni el concepto de fragmentación). Si lo necesitás para el TP (por overhead de encapsulamiento en VXLAN, por ejemplo) es conocimiento que tenés que aportar vos, aclarando que va más allá del material de la cátedra.
- Tampoco aparece la palabra "loopback", ni "namespace", ni nada de contenedores/Docker/Kubernetes/Terraform — la materia es de networking clásico "físico hasta Internet", y el puente a IaC/K8s te lo tenés que armar vos (por eso está la Parte 2 de este documento).

---

## Parte 1 — Resumen por clase y práctica

### Clase 1 — Tipos de Vínculos (capa física)

- Objetivo declarado de la materia: pasar de "en mi PC funciona" a entender una app clusterizada en un datacenter híbrido multi-región — **este es el marco conceptual bajo el que se inscribe todo el TP**.
- Evolución de temas de la materia declarada en el primer slide: Entorno oficina → Entorno Edificio → Entorno Campus → Entorno Internet → Entorno Nube → Servicios. El TP de Terraform/K8s cae del lado de "Entorno Nube/Servicios".
- Tipos de vínculo guiado (cableado): **Cobre** (Coaxil, UTP, Par telefónico), **Fibra óptica** (Monomodo, Multimodo), **Ondas electromagnéticas** (Radiofrecuencia, Microondas, Satélites).
- Coaxil: más inmune al ruido, cables modernos llegan a 1GHz de ancho de banda, costo medio.
- Par trenzado (UTP): el trenzado elimina crosstalk; CAT7 llega a 600MHz de BW. Velocidades: **UTP CAT5 = 100Mbps, CAT5e = 1000Mbps, CAT6 = 10Gbps**. Frase textual: "La clave es leer el cable".
- Fibra óptica: inmune a EMI, decenas de Gbps. **Multimodo**: distancias cortas (<1km), cobertura color **naranja**. **Monomodo**: distancias largas (>1km), cobertura color **amarilla**. Partes: **Core = núcleo**, **cladding = revestimiento**.
- Cables submarinos: transportan ~99% de las comunicaciones de Internet, del orden de Tbps, ~575 cables en el mundo. Se alimentan por corriente eléctrica que lleva el propio cable (amplificadores ópticos, sin conversión a señal eléctrica en el trayecto).
- Medios no guiados: antenas direccionales (línea de vista, propagación por espacio libre, velocidad → c) vs omnidireccionales. Bandas: **2GHz–40GHz** microondas/punto a punto/satélite; **30MHz–1GHz** omnidireccional/broadcast; **3×10¹¹–2×10¹⁴** infrarrojo local. Radioenlace terrestre: fórmula de línea de vista **D = 7,14·√((4/3)·h)**.
- Satélites: **GEO** (36.000km, gira en 24hs con la Tierra), **MEO** (10.000–20.000km, no giran con la Tierra), **LEO** (~5.000km o menos, requieren "tren" de satélites o antenas que sigan el movimiento). Latencia GEO ≈ **120ms** (36.000km / 300.000km/s). Se necesitan **3 satélites** para cubrir toda la Tierra en GEO.
- Estadísticas satelitales: 4857 en órbita total, 1980 activos (40%), 2877 en desuso (60%); de los activos: GEO 30%, MEO 6%, **LEO 63%**, elípticos 1%. Ejemplo Starlink: primera órbita 550km, segunda 1110km; promete 20-40ms de latencia y 50-150Mb/s.
- VSAT (Very Small Aperture Terminal, 1-2m de diámetro vs hasta 10m de antenas GEO tradicionales): no tienen potencia para comunicarse VSAT-VSAT directo, necesitan hub terrestre; desventaja de doble camino agrega ~512ms de latencia.
- Repaso de teoría de señales: **Belio = log(potencia/referencia)**; **Decibel: dB = 10·log(S/N)**; **dBm** = referenciado al miliwatt (mW).

---

### Clase 2 — Cableado, Dispositivos de Red, Wifi

Es la clase más extensa (cableado estructurado + Ethernet/switches + VLAN/STP + diseño de redes + routers + WiFi completo). La agrupo en sub-temas.

**A) Cableado estructurado**
- Norma **EIA/TIA 568**. Ventaja declarada: independiente de aplicación/proveedor, permite mover personal sin recablear, ubicación centralizada facilita localizar fallas.
- Históricamente instalaciones **heterogéneas** (telefonía CAT2 + datos UTP) vs **homogéneas** (solo UTP o MMF).
- Rack: **1U = 1,75" = 4,445cm**; ejemplos de racks de 40U y 12U. Distinción entre racks "prolijos" (con ordenador de cables) y "no prolijos".
- Subdivisión del cableado: **cableado de campus** (entre edificios), **vertical**, **horizontal**, **de usuario**.
- **Cableado horizontal**: topología en **estrella**, máximo **90 metros** desde el área de trabajo (WA) hasta el armario de telecomunicaciones del piso; patch cords/cables en el WA no superan **5 metros**. Regla de cálculo usada: cable de usuario ≈ 3m, cable en el patch panel ≈ 7m (sumado a los 90m horizontales).
- Puesto de trabajo: **roseta** (jack RJ-45 hembra) + patch cord UTP o de fibra óptica.
- Tester de cable UTP verifica: conectividad de pares, pinout/norma, *opens*, cortocircuitos, pares invertidos/cruzados.
- **Cableado vertical ("backbone")**: conecta pisos, normalmente con redundancia (topología en **anillo** si hay redundancia, en **cascada** si no la hay); suele ser el enlace de mayor velocidad de la red.
- Data centers: **piso técnico/raised floor**, bandejas de cableado aéreas (**overhead cabling trays**).

**B) Ethernet: hub → bridge → switch**
- Trama Ethernet con tamaños exactos de campo: **Preámbulo 7B, Inicio de Frame 1B, MAC Destino 6B, MAC Origen 6B, VLAN tag (opcional) 4B, Type/Length 2B, Payload 46-1500B, CRC 4B, Inter Packet Gap 12B**.
- Medio compartido original: **CSMA-CD** (Carrier Sense Multiple Access with Collision Detection).
- **Hub**: capa 1, siempre hace broadcast (no toma decisiones).
- **Bridge**: capa 2, conecta 2 LAN, decide qué frames pasan, **divide dominios de colisión**, hoy se usa "en forma virtual"; como equipo físico se lo puede usar como **"stealth firewall"**; no cambia topología ni gateways, **no se ve en un traceroute**. Funcionamiento: al inicio floodea (broadcast) mientras arma su tabla de MACs aprendiendo por el campo *source*; una vez con tabla completa, filtra y solo reenvía por el puerto correcto (o hace flood si el destino es la MAC de broadcast `FF:FF:FF:FF:FF:FF`).
- **Switch** = "bridge" de más de 2 puertos; arma tabla de switching automáticamente; maneja **Unicast, Broadcast y Multicast**. Tres tipos: **Switch L2 Unmanaged**, **Switch L2 Managed**, **Switch L3**.
- Unmanaged: plug & play, sin IP, 10M/100M/1G/10G, 4 a 24 puertos.
- Managed L2: VLANs, **Stacking**, **Link Aggregation**, Multicast, **STP/RSTP**, priorización de tráfico (**CoS**), rate limiting, **SNMP/RMON**.
- Managed L3: toda la funcionalidad L2 + **IP Routing** (estático y RIP; avanzado OSPF/IGRP/BGP), ruteo entre VLANs — **remarcan explícitamente que NO poseen puertos WAN**.
- Ejemplos comerciales citados con specs: 3Com SuperStack 3 (L2, 24 puertos Gigabit + 4 SFP, LACP hasta 8Gbps, fabric 48Gbps, hasta 254 VLAN, RSTP); Cisco Catalyst 3560 (L3, RIPv1/v2/RIPng básico, OSPF/IGRP/EIGRP/BGPv4 avanzado, IPv6 con OSPFv3/EIGRPv6, 32Gbps forwarding); Cisco Catalyst 9600 (25.6 Tbps forwarding, hasta 48 puertos de 100GbE, 8 RU).
- **Stacking**: puertos especiales de interconexión, **una sola IP de administración**, roles **MASTER**/**SLAVE**/miembros, todos con ID único, típicamente en anillo, **deben ser de la misma marca (propietario)**.

**C) VLAN y Spanning Tree**
- Tag 802.1Q insertado en la trama: **TPID 16 bits (0x8100), Priority 3 bits, DEI 1 bit, VLAN ID 12 bits**.
- VLAN: **"Define dominio de Broadcast (para ARP por ejemplo)"**, separa tráfico, **"Permite tener IP overlapping"**, se configura en switches o hosts, requiere switch Managed L2 o L3.
- **VLAN Untagged**: el host no tiene VLAN configurada; el switch agrega el tag al recibir por un puerto untagged y lo quita al enviar por ese puerto.
- **VLAN Tagged**: el host sí conoce su VLAN; el switch espera y mantiene el tag; un puerto tagged puede tener una **"Native VLAN"** para el tráfico untagged que le llegue.
- **STP (Spanning Tree Protocol)**: IEEE **802.1D**; resuelve el problema de loops con enlaces redundantes; **BPDU** por defecto cada **2 segundos**; elige un nodo **root** (por MAC del switch + priority configurable), cada switch elige su **root port** (menor costo al root) y bloquea enlaces que causarían loop, dejándolos de backup.
- Tabla de costos STP vs RSTP citada explícitamente: 10Mbit/s = 100/2.000.000; 100Mbit/s = 19/200.000; 1Gbit/s = 4/20.000; 10Gbit/s = 2/2.000; 100Gbit/s = N/A/200; 1Tbit/s = N/A/20 (formato: costo STP original / costo RSTP actualizado).

**D) Diseño de redes y PoE**
- Jerarquía clásica: **Access Layer → Distribution Layer → (Core Layer en diseños más grandes) → Internet**.
- Data center **legacy**: L3 arriba, L2 abajo, tráfico predominante **"North/South"**.
- Data center **Spine/Leaf**: spine y leaf en L3, solo L2 en el último tramo hacia el host; habilita predominancia de tráfico **"East/West"**. *(Muy relevante como analogía para el TP: un clúster de microservicios también es mayoritariamente tráfico East/West entre pods.)*
- **PoE (Power over Ethernet)**: IEEE **802.3af**, usa los pares de datos para alimentar teléfonos IP, Access Points, cámaras IP, control de acceso.

**E) Routers**
- Conectan dos redes distintas haciendo *forwarding* de paquetes; "usualmente se refiere a la conexión de LAN a WAN"; el slide menciona NAT como tema a ver más adelante (queda para Clase 6).
- Tipos de línea WAN: **línea dedicada** (hasta 1Gbps/T3, suele usar HDLC o PPP), **MPLS** (QoS garantizada por el proveedor), **DSL/Cable/Fibra**, **Wireless** (4G/5G pública o privada).
- Vínculos WAN comerciales: **Punto a Punto** (velocidad total subida+bajada acordada), **LAN to LAN** (10/100Mbps/1Gbps sobre backbone del proveedor), **Fibra oscura** (pares de fibra tendidos y no usados por la empresa, comercializados).
- Comparación explícita **Router vs Switch Capa 3**: Router → WAN, soporta PPP/Frame Relay/OSPF/RIP, ruteo por software muy flexible con tablas grandes, BW/pps limitado, algunos con redundancia WAN/load balancing. Switch L3 → LAN, rutea principalmente entre VLANs, no soporta protocolos WAN específicos, ruteo por hardware, gran capacidad de paquetes.

**F) WiFi**
- **IEEE 802.11x**, define capas 1 y 2, similar a Ethernet pero con diferencias.
- Medio compartido por canal: solo transmite uno a la vez (incluido el AP); si un transmisor falla reiteradamente, baja su velocidad.
- Problemas de medio compartido: **"Near-Far problem"** e **"Hidden Node problem"**.
- Solución: **CSMA-CA** (espera random antes de re-chequear y transmitir; espera ACK tras transmitir, si no retransmite y baja velocidad); **RTS/CTS** solo para paquetes grandes.
- Elementos: **Cliente** y **AP** (Access Point — puede o no estar co-localizado con el router, puede dar interconexión con la red Ethernet).
- Tipos de trama: **Management** (Beacon, Authentication, Association), **Control** (RTS/CTS, ACK), **Data**.
- Trama MAC WiFi con campos exactos: PLCP Preámbulo 16B, PLCP Header 2B, Frame Control 2B, Duration 2B, Addr1/2/3 6B cada uno, Seq 2B, Addr4 0/6B (opcional, mesh), Payload 0-2304B, Trailer 4B. Subcampos de Frame Control: Version, Type, Subtype, To DS, From DS, Frag, Retry, Pwr, Data, WEP, Order.
- Direcciones MAC típicas usadas (3): Source, Destination, **BSSID** (MAC del AP); la 4ta es opcional (mesh).
- **Beacon** incluye: SSID, supported rates, info de canal, intervalo de beacon (sync/power mgmt), opciones de seguridad soportadas, QoS/Traffic Indication Map.
- Conexión: **Autenticación → Asociación (Association Request/Response con "capabilities") → Key Exchange** (claves de encriptación).
- Seguridad WiFi: **WEP** (inseguro, sin soporte de servidor de autenticación), **WPA** (soporta auth server, pero TKIP inseguro), **WPA2** (AES, vulnerable a passwords simples), **WPA3** (SAE, "el más seguro actualmente").
- Estándares: **802.11g** 2.4GHz/54Mbps; **802.11n** 2.4&5GHz/600Mbps; **802.11ac ("WiFi-5")** 2.4&5GHz/1-3.5Gbps; **802.11ax ("WiFi-6")** 2.4&5GHz/1.2-9.6Gbps.
- WiFi6 sobre WiFi5: **OFDMA** (multi-destino en el mismo paquete); evolución MIMO: pre-WiFi5 = SU-MIMO; WiFi5 = MU-MIMO solo descarga (hasta 4 dispositivos); WiFi6 = MU-MIMO descarga y subida (hasta 12 dispositivos).

---

### Clase 3 — Protocolos de ruteo

- **Sistema Autónomo (AS)**: conjunto de redes administradas por la misma entidad, rige una sola política de ruteo.
- **IANA** otorga IPs y ASN a los 5 registros regionales (RIR): **AfriNIC, APNIC, ARIN, LACNIC, RIPE NCC**. Ejemplos reales de WHOIS de LACNIC citados: `190.188/15` (Prima S.A., ASN 10834) y `209.13/16` (Telefónica Data Argentina, ASN 7934).
- Protocolos **EGP** (exterior, entre AS — se identifican con **ASN** provisto por IANA, se usan típicamente al cambiar de país/empresa) vs **IGP** (interior, dentro de un AS, diseñados para redes más chicas). Para operar, un EGP necesita: lista de routers vecinos, lista de redes propias a publicar, y el ASN local.
- Ruteo **estático** (no decide según estado de la red) vs **dinámico** (cambia decisiones según estado de la red).
- Tres familias de ruteo dinámico:
  - **Estado de enlace (link-state)**: cada nodo anuncia a **todos** los nodos sus redes+costos; cada nodo arma un mapa completo de la red e itera para hallar el camino de menor costo. Genera mucho tráfico, poco recomendado para redes grandes.
  - **Vector distancia (distance-vector)**: los nodos anuncian solo a sus **vecinos**, y anuncian costos (no topología). Rápido para agregar nodos nuevos; lento para converger cuando un nodo "muere" (problema de "distancia infinita").
  - **Path vector**: mejora sobre vector distancia — cada nodo pasa el **path completo** que conoce (sirve para detectar loops). La decisión de armado puede considerar distancia, ancho de banda, o **factores económicos**. **BGP usa path vector**, con configuración manual.
- **BGP (Border Gateway Protocol)**: protocolo estándar de conexión entre AS; el objetivo de fondo es "limitar conexiones" (los ISP quieren controlar qué tráfico pasa por ellos, por motivos económicos); no siempre elige el camino más corto; **corre sobre TCP puerto 179**. Dos modos: **iBGP** (entre routers del mismo AS) y **eBGP** (entre AS distintos) — el criterio es: mismo ASN entre peers = iBGP, distinto ASN = eBGP.
- Tres tipos de redes en Internet (BGP): **Red Stub** (una sola conexión, no hace tránsito), **Red de multiconexión** (más de una conexión, pero rechaza paquetes con AS origen/destino desconocidos), **Transit Networks** (dejan transitar tráfico de terceros, pueden restringir y cobran por el tránsito).
- Políticas de BGP pueden ser de carácter seguridad, político o económico (ejemplos citados: "no pasar tráfico a ciertos AS", "solo transitar por Albania si no hay otro destino posible", "tráfico de/hacia IBM no debe transitar por Microsoft"). Ante rutas múltiples, BGP elige la de **menor cantidad de AS** en el path (AS-path más corto).
- **BGP Next-Hop**: dentro del AS los routers comparten tablas vía iBGP, pero para llegar al next-hop anunciado se necesita **un IGP o una ruta estática** adicional.
- **BGP Blackhole**: mitigación de DDoS anunciando una ruta /32 (o /128 en IPv6) hacia un destino de "descarte"; puede ser local o **RTBH (remote triggered black hole)**, que requiere soporte del **carrier de tránsito**. Ventaja: detiene el ataque antes de tu router de borde. Desventaja: el cliente atacado queda "sin Internet", requiere soporte del carrier y un sensor que automatice detección/bloqueo.
- Herramientas prácticas mencionadas: **MTR** (my traceroute, muestra los AS de tránsito), **traceroute -A**, **BGPview.io** (gráfico de upstreams).
- **Métricas de ruteo**: conteo de saltos, ancho de banda, carga, retardo, confiabilidad, costo.
- **Distancia Administrativa (AD)**: entero entre **0 y 255**; resuelve qué ruta usar cuando la misma red se conoce por distintos protocolos (menor AD gana). *(Nota: el PDF no trae la tabla de valores por defecto de cada protocolo — solo un ejemplo donde EIGRP le gana a RIP por tener menor AD — así que los valores clásicos (Directa=0, Estática=1, EIGRP=90, OSPF=110, RIP=120, etc.) hay que repasarlos aparte si los preguntan.)* Si cae el enlace por el que se aprendió la ruta de menor AD, el router puede usar la ruta alternativa (ej. RIP) que ya tenía almacenada.
- **IGRP** (Cisco, antecesor de EIGRP, considerado obsoleto): métrica compuesta de BW+retardo+carga+confiabilidad, actualizaciones broadcast cada **90 segundos**.
- **EIGRP** (Cisco): sin actualizaciones periódicas (solo ante cambios de topología), permite balanceo de carga con costos distintos, adyacencia por "saludo" EIGRP, métrica basada en BW mínimo + retardo acumulado, guarda en base de datos **todas** las rutas recibidas (no solo la mejor) → convergencia rápida ante fallas.

---

### Clase 4 — Redes WAN. MPLS, PPP y PPPoE. Calidad de servicio

**A) Protocolos y tecnologías WAN**
- Objetivo WAN: conectar sitios/centros de cómputos a grandes distancias.
- Capa de enlace en WAN: agrupa bits en tramas; dos tipos de redes: **broadcast** (generalmente LAN) y **punto a punto** (generalmente WAN).
- Capa física WAN — ejemplos de estándares citados: **EIA/TIA 232, EIA/TIA 449, V.35, X.21, G.703, RS-422**.
- **Línea dedicada**: punto a punto, hasta **45 Mbps (T3)**, la más cara, suele usar **HDLC o PPP**. **Última milla**: la conexión final del ISP al cliente.
- Tipos de conmutación: **de circuitos** (POTS), **de paquetes** (X.25, Frame Relay), **de celdas** (ATM — "puede ser tecnología WAN o LAN").
- Protocolos punto a punto: **SLIP** (primero en encapsular IP sobre líneas serie), **HDLC** (orientado a bit, formato único de trama, default en interfaces seriales de routers Cisco desde 1979), **PPP** (basado en HDLC, muy usado en conexiones hogareñas).
- **Frame Relay**: pensado para líneas de alta calidad/velocidad, sin buen control de errores (delega en capa superior), cada router necesita solo 1 interfaz física, reemplazo de X.25. Usa **DLCI (Data Link Connection Identifier)** para armar **circuitos virtuales permanentes (PVC)** (ejemplo con 4 CVP entre sucursales, cada uno como cadena de DLCIs).
- **PPP** en detalle: soporta IP/IPX/AppleTalk, autenticación **PAP y CHAP**, asignación dinámica de IP, detección de errores. Trama: **Flag** (valor fijo `01111110`), **Dirección** (fijo `FFh` en punto a punto), **Control** (fijo `03h`, trama no numerada), **Protocolo** (identifica el protocolo del payload), **FCS** (chequeo de trama).
- Ejemplos reales de red WAN con sucursales y CIDR: Sucursal 1 = `10.4.14.0/23` (Buenos Aires); Sucursal 2 variando entre `192.168.4.0/24` (Bs. As.), `192.168.100.0/24` (Bahía Blanca), `192.168.115.0/24` (Ushuaia), `192.168.168.0/24` (Córdoba) — con tracert de un extremo al otro.
- **Metro Ethernet**: tecnología para MAN, capa 2, crea una **EVC (Ethernet Virtual Connection)** punto a punto (hoy 1-10Gbps), usada para unir dos data centers (principal/contingencia), cara. El proveedor "presenta una LAN virtual entre los dos sitios".
- Enlaces hogareños: **ADSL** con **PPPoE** (PPP sobre Ethernet); **cable módem** con protocolo **DOCSIS** (estándar mundial de operadores de cable).
- **ADSL**: Asymmetric DSL, usa el par de cobre telefónico, hasta 5,5km de la central, normas **ANSI T1.413** e **ITU G.992.1**, hasta 8Mbps bajada / 1Mbps subida; filtro pasa-bajos (4000Hz) para el teléfono y pasa-altos (26KHz) para el módem.
- Ejemplos de cable módem citados: Motorola SurfBoard 5101 (DOCSIS 2.0, hasta 38Mbps down/30 up) y 5121 (DOCSIS 2.0, soporta SIP, hasta 51Mbps down/30 up).

**B) Calidad de Servicio (QoS)**
- QoS surge para priorizar servicios ante **congestión** (ejemplos que no toleran congestión: videoconferencia, VoIP). "QoS sirve **solo** cuando hay congestión en el enlace". No confundir con **Aceleración WAN** (que optimiza BW con compresión/deduplicación en origen y destino, no es QoS).
- En Internet: casi imposible de aplicar, los routers ofrecen **"Best Effort"**. En WAN/LAN propia: posible, depende de si los routers son administrados por un tercero o por uno mismo.
- Técnicas de QoS: aumento de BW, **buferización**, normas de encolamiento, **clasificación (etiquetado)**.
- **Buferización**: se hace en el receptor, no afecta BW, incrementa retardo, **decrementa jitter**; no sirve para videoconferencia/VoIP, sirve para **streaming** (sitios comerciales suelen usar buffers de ~10 segundos).
- Tipos de cola: **FIFO** (sin QoS, descarta si se llena), **de prioridad** (4 colas: alta/media/normal/baja, nombres comerciales "Multimedia/Oro/Plata/Bronce"; riesgo de inanición de las colas bajas), **personalizada** (round-robin, se define tráfico/cantidad de paquetes/BW por cola — sin inanición pero sin garantías estrictas de prioridad), **WFQ (Weighted Fair Queueing)** (automatizado, cola separada por tipo de tráfico según IP/puerto origen-destino, prioriza flujos de bajo caudal y sensibles a retardo como VoIP, alto uso de CPU).
- **Clasificación**: puede ser en capa 2 o 3. En **capa 3**: campo **ToS** de IPv4 se convierte en **DSCP** (Differentiated Services Code Point, **RFC 2474**). En **capa 2**: **IEEE 802.1p**, que usa la extensión **802.1Q** (la misma de VLANs), trabaja a nivel MAC.
- Clasificación también por **ACL (Access Control List: dirección IP, puerto)**, tipo de aplicación (streaming/VoIP/archivos), **DPI (Deep Packet Inspection)**, puerto del switch.

**C) MPLS**
- **Multiprotocol Label Switching**: asigna a los datagramas una **etiqueta (label)** para conmutación rápida — los routers intermedios **solo miran la etiqueta**, no el destino. Las etiquetas definen un **circuito virtual** a través de toda la red.
- Etiquetado en capa 2 o 3; permite QoS independientemente de la red subyacente.
- Header MPLS de **4 bytes** entre el header de nivel 2 y el header IP: **Label 20 bits, QoS/EXP 3 bits, S (bottom-of-stack) 1 bit, TTL 8 bits**.
- Armado del camino (*path*): un router consulta al siguiente por la etiqueta a usar (**"label request"**) y este responde con el mapeo (**"label mapping"**), armando tabla `If In / Lbl In / Addr / Lbl Out / If Out` en cada salto hasta crear el camino virtual completo.
- Caso de uso citado: red de servicios centralizados con navegación, mail, file servers, VoIP, videoconferencia y apps web, cada uno con prioridad Oro/Plata/Bronce.

---

### Clase 5 — Internet, IXP

- **Tipos de ISP**: cada ISP paga "tránsito IP" hacia arriba en la jerarquía a valores altos.
- **Peering**: "libre de acuerdo". **Peering privado** (interconexión física voluntaria entre 2+ ISP, vía LAN-to-LAN, fibra oscura, etc. — se usa para evitar consumir upstream/IP transit). **Peering público**: a través de un **IXP**, reduce gastos del ISP.
- **NAP (Network Access Point) / IXP (Internet Exchange Point)**: producen el intercambio de tráfico entre redes de operadores, ISP, gobierno, academia, etc. Beneficios: menor costo, **menor latencia**, desarrollo de contenido local, mejor confiabilidad/redundancia. Topología típica: switch de alta velocidad donde los routers de cada miembro hablan entre sí con un **EGP (ej. BGP)**.
- **CABASE** ("Cámara Argentina de Internet"), agrupa los IXP de Argentina. Cronología citada: 1989 inicio de actividades; 1997, 18 miembros fundan el NAP CABASE; 1998 arranca operaciones; 2005 parámetros de QoS; 2006, 44 miembros + primer Route Server del país + lanzamiento de conectividad IPv6; 2010 NAP regionales; **2025: 28 IXP, 600 miembros, 24 millones de usuarios finales**. Comparación: España 18 IXP, Portugal 6 IXP.
- Miembros de ejemplo citados de CABASE: Fibertel/Cablevisión, Telmex Argentina, Telecentro, AFIP, AT&T, UTN, Meta, Riot Games, Banco Provincia, Amazon.
- Datos técnicos reales de IXP de CABASE (**muy citables para justificar bloques de red en el TP, aunque sean de otro contexto**): **IXP Buenos Aires**: 186 participantes, IPv4 `200.0.17.0/24`, IPv6 `2001:13c7:6001::/48`, **ASN 11058**. **IXP La Plata**: 21 participantes, `200.115.81.0/24`, IPv6 `2001:13c7:6011::/48`, ASN 52375. **IXP Puerto Madryn**: 11 participantes, `200.115.84.0/24`, IPv6 `2001:13c7:6014::/48`, ASN 522294.
- **PAT (Punto de Agregación de Tráfico)**: PoP cerca de un IXP regional, ofrecido por un "miembro PAT", con vínculo y switch provistos por ese miembro y homologados por CABASE regional.
- **Carriers**: operadores dueños de las redes troncales de Internet, responsables del transporte de datos, dan conexión de alto nivel.
- **AS en empresas**: muchas empresas arman su propio AS (deben registrarse en IANA y comprar IP públicas). Caso citado: **Toyota Argentina**, ASN **28034**, red propia **200.7.15.0/24**, con dos proveedores (Techtel y Telecom).
- **Looking Glass servers**: servidores de solo lectura (suelen ofrecerlos los ISP) que dan bgp/ping/traceroute vía web, o acceso telnet de solo lectura. CABASE tiene el suyo (`looking.cabase.org.ar`), permite elegir desde qué IXP operar.
- **Balanceo de carga y contenidos**, por niveles: **a nivel IP**, **a nivel DNS**, **a nivel servicios (balanceadores)**, **a nivel objetos (CDN)**.
- **Anycast**: una IP puede corresponder a varios servidores (relación **1-a-muchos**, vs. unicast 1-a-1); no soportado oficialmente por IPv4 pero sí por IPv6; ventajas: velocidad de ruteo/baja latencia, redundancia, mitigación de DDoS, balanceo de carga; contra: difícil de implementar; lo usan DNS y CDN. Funciona apoyado en BGP (el router de borde "cree" que hay un solo destino aunque en realidad hay servidores físicamente distintos en cualquier lugar). Ejemplo citado: `8.8.8.8` (DNS de Google). **Frase clave para el TP**: *"Se suele armar un cluster de servidores internos usando la misma tecnología de Anycast para la LAN"*. En Argentina: Proyecto **RANA** (Red Anycast de NIC Argentina, desde 2017) para DNS de `.ar`, con modelo centralizado en Bs.As. y distribuido en nodos regionales.

---

### Clase 6 — ISPs, NAT, VPN, DMZ

**A) Arquitectura del ISP**
- Cadena completa: **Casa del cliente → Red de Acceso (Access) → Red de Agregación/Distribución (Aggregation) → Red de Borde (Edge) → Red de Núcleo (Core) → Other ISPs/IXPs**.
- **Access Network**: llega hasta la casa del usuario. **Aggregation Network** (= distribución): consolida tráfico de distintas partes de la red de acceso, en múltiples capas. **Edge Network**: termina el tráfico de usuarios (autenticación, control de ancho de banda) y/o interconecta con otras redes (ISP/IXP). **Core Network**: interconecta todo el ISP internamente, en particular conecta los Edge entre sí.
- Dispositivos típicos por capa: **Peering Router** (hacia el IXP), **Edge Router / BNG / B-RAS**, **Aggregation Switch**, **OLT/CMTS/DSLAM** (concentrador de acceso), **CPE** (equipo del cliente), **Core Routers**.

**B) NAT**
- NAT **no está estandarizado en detalle** (RFC 1631 es "muy general"). El NAT tradicional **no acepta conexiones entrantes salvo que hayan sido salientes primero** (diseñado para modelo cliente/servidor). **NAT no desaparece con IPv6** porque siguen existiendo firewalls y redes públicas/privadas.
- **SNAT (Source NAT)**: dispositivo en red privada contacta a uno en red pública (típicamente un servidor); se arma una asociación `IPA:PortA <-> IPNPub:PortNPub | IPB:PortB`.
- **DNAT (Destination NAT)**: dispositivo en red pública inicia conexión hacia uno en red privada (típicamente un servidor detrás del NAT).
- **Tipos de NAT (variantes de SNAT)**:
  - **Full Cone**: poco restrictivo para entrantes, mapeo estático — asociación `(Aa:Ap,Na:Np) <=> *:*` (cualquiera puede usar el mapeo una vez creado). Bueno para publicar servidores.
  - **IP Restricted**: restringe solo la IP entrante, no el puerto — `(Aa:Ap,Na:Np) <=> B:*`.
  - **Port Restricted**: restringe IP y puerto entrante — `(Aa:Ap,Na:Np) <=> B:Bp`.
  - **Symmetric**: cada nueva conexión (por destino) genera un **puerto externo nuevo** — nunca `Np = Ap` salvo casualidad, a diferencia de los otros 3 tipos donde se intenta mantener `Np = Ap` y se reutiliza el mismo mapeo externo para cualquier destino.
- **NAT Traversal**: problema de conectar 2 PCs detrás de firewall/NAT (P2P, VoIP) sin poder crear reglas entrantes para todos los clientes posibles. Soluciones: **UDP Hole Punching, STUN, TURN, ICE**.
  - **UDP Hole Punching**: sin servidor (ambos extremos conocen puertos de antemano) o con servidor de señalización (coordina IP:puerto de cada lado vía conexiones TCP permanentes, luego cada lado intenta conectar al otro para "perforar" el NAT). Técnica no estandarizada; si falla, hay que hacer *relay* por servidor (alto uso de recursos, limita BW/latencia).
  - **STUN** (Session Traversal Utilities for NAT, **RFC 5389**, antes RFC 3489): protocolo para descubrir el tipo de NAT y permitir a un cliente conocer su IP:puerto público de salida; chequea conectividad entre 2 endpoints. Servidores STUN gratuitos citados (ej. `stun.ekiga.net`). No suelen ofrecer relay.
  - **TURN** (Traversal Using Relay NAT, **RFC 5766**): debería ser la segunda opción si STUN falla; hace relay de UDP/TCP; **única solución para NAT Symmetric**.
  - **ICE** (Interactive Connectivity Establishment): evalúa todos los candidatos (STUN/TURN/IPs locales), los ordena por prioridad, chequea conectividad, y deja de operar una vez establecida la conexión.
  - Caso de uso detallado: **UDP Hole Punching en VoIP/P2P** con proxy SIP + STUN, describiendo paso a paso el intercambio de INVITE/SDP entre A y B via PBX.
  - **Double NAT**: caso SNAT+DNAT cuando cliente y servidor están cada uno en su propia red privada; caso SNAT+SNAT en P2P donde "no es práctico configurar reglas de NAT manualmente (DNAT)".

**C) VPN**
- **VPN (Virtual Private Network)**: interconecta redes/equipos a través de otras redes; si atraviesa redes de terceros hay que aplicar **encriptación**; se la llama "túnel" porque encapsula la comunicación entre las 2 puntas.
- Modos de conexión: **Cliente a Sitio** (uso típico: usuarios móviles; licencia por cliente/usuario) y **Sitio a Sitio** (uso típico: sucursales por Internet, interconexión entre empresas; licencia por sitio).
- Tipos de solución: **Hardware** (firewall), **Software** (cliente-servidor), **Mixtas**.
- **Capas de una VPN** (diagrama explícito): autenticación (**CHAP, PAP, EAP**) + encriptación (**IPSEC, SSL**) sobre un **protocolo de túnel** (**GRE, L2TP, PPTP**), todo por encima/debajo del datagrama L3 real. Ejemplo de layering completo mostrado: `HTTP(L7) / TCP(L4) / IPv6(L3, paquete original) → L2TP(túnel) / UDP(L4) / IPSec(encriptación) / IPv4(L3) / Ethernet(L2) / Ethernet físico(L1)`.
- **Software**: **OpenVPN** — licencia GPL, VPN SSL, **usa un solo puerto UDP**, atraviesa proxy y firewall, **"no tiene problemas con NAT"**.
- **Hardware**: firewalls que soportan VPN cliente-sitio y sitio-sitio, cliente propietario, VPN SSL vía plugin de navegador.
- **IPSec**: definido por IETF en 1998; conjunto de RFCs: **RFC 2401 (IPSec), 2402 (Authentication Header), 2406 (ESP), 2408 (ISAKMP), 2409 (IKE)**; "muy complejo de implementar"; corre en espacio **kernel** del SO.
- Protocolos de autenticación VPN: **EAP** (más seguro), **CHAP**, **PAP** (menos seguro) — intercambian credenciales cliente/servidor VPN, hacen handshake e intercambio de claves/shared secret; durante el handshake se asigna la IP de la interfaz virtual.
- Ejemplo numérico completo de VPN cliente-a-sitio dado en clase (útil como plantilla para el TP): notebook con `eth0 192.168.0.49/24, GW 192.168.0.1, DNS 8.8.8.8`; se conecta a `vpn.miempresa.com.ar (181.22.33.44)`; redes internas de la empresa: `10.4.0.0/16, 10.50.50.0/24, 10.40.1.0/24, 192.168.0.0/16`; tras conectar, aparece `eth1 (virtual) 10.50.50.152/24` y la tabla de ruteo agrega rutas hacia las redes internas por esa interfaz virtual, más una ruta host `/32` hacia la IP pública del VPN server por la interfaz física.

**D) DMZ**
- **Network Edge**: frontera entre red interna (hogar/empresa) y externa (Internet); puede ser "más que el router". Motivos: exponer servicios a Internet, evitar ataques a la red interna, controlar el acceso. Frontera con: Internet, WAN hacia sucursales, usuarios remotos, clouds, *guests*.
- **DMZ (Demilitarized Zone / Zona Desmilitarizada)**: descripta como **"tierra de nadie"**, se usa para exponer servicios externos de forma controlada. Reglas generales (cita textual): **"Internet → DMZ: controlado para servicios específicos"**, **"DMZ → interno: muy restringido, mínimo acceso"**, **"interno → DMZ: generalmente accesible al menos para management"**, **"Internet → interno: bloqueado!"**.
- Topologías mostradas: **DMZ con 1 firewall** (un único firewall con 3 interfaces: externa/DMZ/interna) y **DMZ con 2 firewalls** (uno entre Internet y DMZ, otro entre DMZ e interna — defensa en profundidad).
- **Jump Server**: controla el acceso administrativo a los distintos servidores de la DMZ; mitiga el riesgo de **"side channel attack"** (que desde un servidor comprometido se acceda al resto); da acceso administrativo solo a usuarios específicos hacia servidores específicos, **auditado**, y "muy seguro, solo levanta y abre los puertos y servicios mínimos".

---

### Lab 1 — Repaso y Direccionamiento

- Guía de ejercicios de repaso: clases de direcciones (A/B/C/D/E — rango Clase C = **192-223**), protocolo para resolver MAC desde IP local (**ARP**, no RARP/BOOTP), qué usa **ICMP** (ping, traceroute — no ARP, que es su propio protocolo), MAC de broadcast = todos **unos** (no ceros — pregunta trampa, la opción "todos ceros" es la incorrecta), MAC definida en capa de enlace (no de red — otra trampa), gateway = entrada **`0.0.0.0`** de la tabla de ruteo.
- **RIP analiza la cantidad de saltos al destino** (no analiza estado del link, ni congestión, ni busca el camino más corto en términos de ancho de banda — es vector-distancia puro por hop count).
- Ejercicio de **resolución de nombres DNS** paso a paso desde el navegador de una casa con Arnet: intervienen (en orden) navegador → archivo hosts → servidor DNS de Arnet → root server → NIC.AR → servidor DNS del dominio → servidor DNS del subdominio `www` — practica la cadena jerárquica completa de resolución.
- Ejercicios de **subneteo/VLSM** con notación `/nn`: calcular máscara, red, broadcast, rango y cantidad de hosts para `172.16.37.142/20`, y verificar si otra IP cae en la misma subred.
- Ejercicio de **VLSM para 5 departamentos iguales** sobre `192.168.50.0/24` (25 dispositivos cada uno).
- Ejercicio de **VLSM con bloques de distinto tamaño** sobre `192.168.10.0/24` (Ventas 100 equipos, Ingeniería 50 equipos + gateway), comparando asignar de mayor-a-menor vs menor-a-mayor y cómo cambia el espacio libre resultante — **exactamente el tipo de razonamiento que hay que aplicar para justificar los bloques del TP** (pod CIDR, service CIDR, etc. sin que se solapen y dejando margen para crecer).
- Ejercicio de **VLSM con crecimiento futuro** sobre `192.168.20.0/24`: Administración `/26` (50 disp.) y Soporte `/27` (20 disp.) ya asignados, evaluando si más adelante entra un Desarrollo `/25` (100 disp.) sin romper lo existente, según el orden en que se ubiquen los bloques — **relevante para argumentar por qué conviene dejar rangos "alineados" y con margen libre al diseñar el pod CIDR/service CIDR del clúster**.

---

### Lab 2 — Cableado Estructurado

- Ejercicios de diseño de cableado estructurado para edificios de varios pisos: ubicación del centro de cómputos, topología tolerante a fallas, cálculo de metros de fibra/cable/cable-canal, cantidad de racks/patcheras/rosetas/conectores RJ-45/patch cords/switches.
- Comparación **VoIP vs Central Telefónica tradicional** en términos de recursos necesarios.
- Ejercicio de dimensionamiento con **10% de reserva de crecimiento** sobre 100 puestos de trabajo (PC + teléfono VoIP), usando patch panels de 24 puertos/1U, switches de acceso de 48 puertos/1U, rack de 42U y 2 switches de distribución/core — calculando enlaces horizontales, rosetas, patch panels, switches, U de rack ocupadas y **cables de backbone** hacia la sala central (y de qué switches del stack deberían salir).
- Ejercicio de ubicación de sala central en un edificio de 6 niveles (zona con riesgo de inundación en planta baja → **no poner la sala central ahí**), con 2 proveedores de Internet entregando en la sala central, definiendo dónde van routers/firewalls de cada proveedor.
- Ejercicio de **Top of Rack (ToR)**: cada ToR con uplink hacia cada switch superior, par de distribución/core con 10 puertos de 100Gb/s para la zona de servidores; calcular ToR necesarios (hoy y tras ampliar de 6 a 13 racks), puertos necesarios en los switches superiores, y **puntos únicos de falla (SPOF)** del diseño — concepto directamente aplicable a discutir redundancia (o falta de ella) en un clúster Kind de un solo laptop.
- Ejercicio de interconexión de un 3er edificio a 350m del edificio central, definiendo dispositivos, cantidad/tipo/recorrido de cables entre edificios.
- Anexo técnico: subsistemas de cableado estructurado — área de trabajo, horizontal, switch de piso/acceso, vertical (backbone), centro de datos, switch de distribución, cableado de campus.

---

### Lab 3 — Switches, Configuración Básica

- Los equipos Cisco tienen **4 modos de configuración**: **User Mode, Privilege Mode, Configure Mode, Interface Mode**.
- Comandos base practicados: `show version`, `show ?`, `enable` (pasa a Privilege Mode), `show running-config`, `hostname <nombre>` (ej. `SW_Piso2`), `show ip interface`.
- Para dar IP de administración a un switch (capa 2) se configura la **interfaz VLAN1** (SVI): `interface VLAN1` → `ip address 10.1.1.1 255.255.0.0` → `no shutdown` (recién ahí responde ping/telnet). Remarca que sin esto **el switch no tiene IP**.
- `show interfaces`, `show interfaces fastethernet 0/1`, `show interfaces fastethernet 0/?` (para listar cuántas interfaces de cada tipo hay).
- Configuración de interfaz puntual: `interface fastethernet 0/1` → `description File_Server` → `shutdown` (deshabilita el puerto; el lab verifica que efectivamente corta conectividad de ese host pero no del resto).
- Persistencia: la config vive en **NVRAM**; `write erase` la borra, `reload` reinicia el equipo (sin guardar, se pierde lo no confirmado).
- Deja explícito que `ping` se puede correr tanto desde User como desde Privilege Mode.

---

### Lab 4 — Switches, VLANs

- `show vlan` muestra el estado; por defecto **todos los puertos están en VLAN 1 ("default")**. Switch usado: **Cisco 2960** (24 puertos FastEthernet 100Mbps + 2 Gigabit).
- Creación de VLAN: `vlan 2` → `name presidencia`. Asignación de puerto: `interface FastEthernet 0/1` → `switchport access vlan 2`. Menciona la existencia de **VLAN dinámicas** (asignadas por MAC del host, no por puerto físico).
- Ejercicios progresivos muestran que **hosts en distinta VLAN no se hacen ping aunque compartan la misma subred IP** (ej. todos en `10.1.1.0/16`) — la separación es a nivel de **dominio de broadcast/VLAN**, no de subneteo IP. Es la demostración práctica de "permite IP overlapping" de la Clase 2.
- **VTP (VLAN Trunk Protocol)**: usado entre switches para sincronizar información de VLANs.
- **Trunk**: `interface Gig0/1` → `switchport mode trunk` (hay que configurarlo en ambos extremos del enlace entre switches para que las VLAN se propaguen entre ellos).
- Ejercicio multi-switch con subredes distintas por VLAN (ej. Switch0 VLAN1 `10.1.1.1/16`, luego VLAN "compras" en `10.2.0.0/16`) mostrando cómo sin trunk configurado ciertos hosts quedan aislados y cómo cambia la visibilidad al habilitar trunk y homologar los números/nombres de VLAN entre switches.
- **Passwords Cisco**: 5 tipos — **consola, auxiliar, VTY (Telnet), enable password, enable secret**. VTY: `line vty 0 15` → `login` → `password itba`. Privilegiado: `enable secret <pass>` (tiene precedencia/es más seguro que `enable password`).
- Persistencia: `copy running-config startup-config` (guarda en memoria **FLASH**), `reload` para reiniciar y confirmar que persistió.

---

### Lab 5 — Routers: Enrutamiento Estático, RIP y OSPF

- **Ruteo estático**: `ip route <red> <máscara> <interfaz>` (ej. `ip route 192.168.1.0 255.255.255.0 GigabitEthernet0/1`). Se configura IP de interfaces y **gateway en cada PC** antes de rutear.
- `show ip route` — códigos de tabla de ruteo explicados: **L (Local)** = interfaz propia del router, **C (Connected)** = redes directamente conectadas, **S (Static)** = redes por ruteo estático.
- Prueba de conectividad end-to-end incluyendo acceso a un servidor web (`http://172.16.2.1`, puerto 80) a través de rutas estáticas en varios routers intermedios.
- **RIP**: se activa publicando redes con el comando `network [red]` en cada router para las redes directamente conectadas.
- **OSPF de área única**: `router ospf 1` → `network [red] [wildcard] area [nro]` — usa **wildcard mask** (máscara inversa), no máscara de subred directa. Verificación: `show ip protocols`, `show ip route`, `show ip ospf neighbors`, `show ip ospf database`.
- **OSPF multi-área**: ejercicio con 3 áreas, remarcando que **"el área 0 es la que conecta las áreas adyacentes"** (área backbone). Mismos comandos de verificación, más `debug ip ospf events` (adyacencias), `debug ip ospf` (paquetes), `debug ip ospf hello` (actualizaciones hello).

---

### Lab 6 — Routers: Ruteo Dinámico (BGP)

- Uso de **Looking Glass servers** públicos (ej. `cogentco.com/en/looking-glass`) para correr traceroute hacia la IP propia del alumno (obtenida antes con `curl ipinfo.io`).
- Conexión por **SSH a "pampero"** (servidor del ITBA) y de ahí por **Telnet a route-views** (`route-views.wide.routeviews.org`, o alternativas `.eqix.` / `.paix.`) — proyecto académico de servidores BGP públicos de solo lectura. Comando clave: `show ip bgp`. Se pregunta explícitamente qué significa la **"i"** al final de cada entrada (BGP: ruta aprendida por IGP) y qué diferencia hay entre lo que se ve en un **router de borde** vs uno **interno**.
- `traceroute` vs **`mtr`** (`sudo apt install mtr`, `mtr --aslookup www.google.com`, `mtr --aslookup -rwbc 10 google.com`) — con `mtr --aslookup` se ve el **ASN de cada salto**; se pregunta por qué el primer salto no tiene ASN (es la LAN propia, no tiene AS) y por qué el resto comparte el mismo ASN (dentro del mismo proveedor/AS hasta salir a otro).
- Lookup de ASN vía LACNIC (`ASN 15169` → Google) y vía `hackertarget.com/as-ip-lookup` para el propio `pampero.itba.edu.ar`.
- Consulta de **rutas BGP hacia un prefijo específico** (`show ip bgp <ip-pampero>`), identificando cuántas rutas conoce el router, cuál es la "mejor", y el **AS-path** completo hasta el destino — remarca que los routers públicos de route-views son **de solo lectura** (solo plano de control/BGP, no permiten ping/traceroute — para eso hay que usar un Looking Glass).
- **RIS/BGPlay de RIPE** (`stat.ripe.net/special/bgplay`) para visualizar en el tiempo cómo cambian las adyacencias BGP de un prefijo (ejemplo usado: `209.13.0.0/16`, red web del ITBA).
- **bgp.he.net**: consulta de cuántos prefijos IPv4/IPv6 tiene asignado un AS, y visualización gráfica de ISPs de nivel superior con ubicación geográfica aproximada.

---

## Parte 2 — Conceptos aplicables al TP de Terraform/Kubernetes

Esta sección es el puente entre la materia y "The Store" corriendo en un clúster **Kind** (Kubernetes-in-Docker) sobre contenedores Docker en tu laptop Linux. Ningún PDF menciona Docker/Kubernetes/Terraform — la cátedra da networking clásico; el mapeo que sigue es la interpretación para el TP, aclarando de qué clase sale cada concepto base. Usalo para escribir el diagrama de arquitectura y para anticipar de dónde puede "tirar del hilo" un profesor.

### 1. Direccionamiento privado y no solapamiento de bloques — *Lab 1, Clase 1*
Tu arquitectura tiene, como mínimo, 4 "capas" de direccionamiento IP anidadas que **no se pueden solapar entre sí**, exactamente el mismo problema que resuelven los ejercicios de VLSM del Lab 1 (comparar asignar bloques de mayor a menor, dejar margen para crecer, etc.):
1. **LAN del host** (tu Wi-Fi/Ethernet de casa, típicamente algo como `192.168.x.0/24`, asignada por tu router hogareño).
2. **Red del bridge de Docker** que crea Kind (por defecto una red Docker `bridge` llamada `kind`, típicamente en `172.18.0.0/16` — Docker la elige evitando choque con otras redes Docker locales), donde viven los **contenedores-nodo** de Kind (cada "nodo" de Kubernetes es en realidad un contenedor Docker).
3. **Pod CIDR** del clúster (rango desde el que Kubernetes asigna IP a cada Pod; con el CNI por defecto de Kind, **kindnet**, suele ser `10.244.0.0/16`, partido en un `/24` por nodo).
4. **Service CIDR** (rango virtual de las **ClusterIP**, típicamente `10.96.0.0/12`).
Estos 4 bloques deben ser **disjuntos** entre sí (y respecto de la LAN real del host) por la misma razón que en el Lab 1 no podés solapar las subredes de dos departamentos: si se pisan, el kernel no sabe a qué interfaz/ruta mandar un paquete y rompés conectividad de forma intermitente y difícil de debuggear. Documentá los 4 bloques en el diagrama con notación `/n`, igual que lo pide la letra del TP.

### 2. NAT / SNAT — el bridge de Docker hace masquerade — *Clase 6*
Cuando un Pod sale a Internet (por ejemplo, para bajar una imagen o llamar a una API externa), atraviesa como mínimo **dos o tres NAT en cadena** — un "Double NAT" (o "Triple NAT") tal cual lo describe la Clase 6:
1. **kube-proxy / iptables** puede hacer NAT de la IP del Pod hacia la IP del nodo (dependiendo del CNI).
2. **Docker hace SNAT (masquerade/overload)** en su bridge: todo lo que sale del contenedor-nodo hacia afuera de la red `kind` se re-escribe con la IP del host Linux (esto es el `iptables -t nat -A POSTROUTING -j MASQUERADE` que Docker configura solo). Conceptualmente es el mismo **SNAT** de la Clase 6 ("dispositivo en red privada contacta a otro en red pública"), aplicado dos veces (Pod→Nodo, Nodo-contenedor→Host).
3. Si tu laptop está detrás de un router hogareño (y quizás detrás de CGNAT del ISP), hay un **tercer SNAT** antes de llegar a Internet real.
Para el oral: el NAT que hace Docker **no es exactamente ninguno de los 4 tipos clásicos (Full Cone/IP Restricted/Port Restricted/Symmetric)** de la Clase 6 tal como se explican para UDP P2P — es un NAT dinámico tipo "overload"/PAT orientado a conexiones salientes TCP/UDP con tabla de conntrack, más cercano en espíritu a Port-Restricted. Vale la pena decir explícitamente en el documento qué tipo de NAT asumís y por qué, porque es justo el tipo de pregunta que van a hacer.

### 3. DNAT / port forwarding — hostPort, NodePort y el mapeo de puertos de Kind — *Clase 6*
Para que algo de afuera (tu navegador, en el mismo laptop o en tu LAN) llegue a un servicio adentro del clúster, se necesita **DNAT** ("dispositivo en red pública inicia conexión hacia uno en la privada"):
- Kind expone puertos del host hacia el contenedor-nodo vía `extraPortMappings` en su config — por debajo es un `docker run -p <hostPort>:<containerPort>`, es decir, **Docker haciendo DNAT** desde la interfaz del host Linux hacia la IP interna del contenedor-nodo en la red `kind`.
- Dentro de Kubernetes, un **Service de tipo NodePort** (o el **hostPort** de un Pod) es la misma idea un nivel más adentro: DNAT desde `<IP del nodo>:<puerto NodePort>` hacia `<IP del Pod>:<puerto del contenedor>`.
- Con un **Ingress Controller** (ver punto 5), agregás un salto más de DNAT/proxy L7 antes de llegar al Pod del microservicio real.
Esto te da 2-3 saltos de DNAT apilados — documentalos todos en el diagrama con el puerto exacto en cada salto (ej. `laptop:8080 → nodo-kind:30080 (NodePort) → pod-ingress:80 → pod-frontend:3000`).

### 4. Bridge de capa 2 y dominio de broadcast — *Clase 2*
La red `kind` (y cada red `bridge` de Docker) es, en esencia, el mismo dispositivo lógico que describe la Clase 2 para el **bridge/switch**: un dominio de broadcast de capa 2 donde los "puertos" son interfaces virtuales `veth` conectadas a cada contenedor, y el propio bridge (`docker0` o el bridge que crea Kind) arma su tabla de forwarding igual que un switch. Dos contenedores en la **misma red Docker** se ven por ARP directo (mismo dominio de broadcast); si están en **redes Docker distintas**, no hay L2 en común y hace falta ruteo L3 (esto es análogo a por qué dos VLAN distintas no se pueden hacer ping sin un router/switch L3 entre medio — Lab 4).

### 5. DMZ → capa de Ingress / borde del clúster — *Clase 6*
El **Ingress Controller** (o, en tu caso, el/los puerto(s) publicados del nodo Kind) cumple exactamente el rol de la **DMZ**: es la única puerta de entrada desde "afuera" (tu navegador / Internet) hacia los microservicios de "The Store", y las reglas de tráfico de la Clase 6 aplican letra por letra:
- **Internet → DMZ (Ingress)**: controlado, solo puertos 80/443 publicados.
- **DMZ (Ingress) → interno (microservicios)**: restringido — el Ingress solo debería poder hablarle a los Services que enruta (frontend, API gateway), no directo a la base de datos.
- **interno → DMZ**: accesible al menos para health-checks/management.
- **Internet → interno**: **bloqueado** — ningún microservicio (catálogo, pagos, base de datos) debería tener un puerto expuesto directamente al host/Internet; todo pasa por el Ingress.
La topología **"DMZ con 2 firewalls"** de la Clase 6 es un buen argumento de diseño en capas: (1) el mapeo de puertos de Docker/Kind como "firewall externo" + (2) NetworkPolicies de Kubernetes como "firewall interno" entre la DMZ (namespace de ingress) y el resto (namespaces de microservicios).

### 6. ACL / NetworkPolicy — *Clase 4 (definición de ACL), Clase 6 (DMZ)*
La Clase 4 define ACL literalmente como **"Access Control List: Dirección IP, puerto"** — es exactamente lo que configura una **NetworkPolicy** de Kubernetes (que filtra por namespace/label selector, IP block, puerto y protocolo). Usalo para justificar reglas tipo "el servicio de pagos solo acepta conexiones entrantes del servicio de checkout, puerto 8443/TCP" como el equivalente Kubernetes-nativo de una ACL de router/firewall. Aclaración importante para el oral: **por default, Kubernetes NO aísla nada** (todos los Pods se pueden hablar entre sí, es "flat network") — las NetworkPolicies son opt-in, al revés de una VLAN que aísla por default y hay que permitir explícitamente.

### 7. VLAN vs. Namespace de Kubernetes — *Clase 2, Lab 4* (distinción importante, posible trampa)
Es tentador decir "un Namespace es como una VLAN", pero **no es cierto** y es un lindo punto para mostrar que entendés la diferencia si te lo preguntan: una VLAN (Clase 2, Lab 4) es aislamiento de **capa 2** (dominio de broadcast distinto, impuesto por el switch, con ping bloqueado entre VLANs por default aunque compartan subnet IP — lo viste literalmente en el Lab 4). Un **Namespace** de Kubernetes es una frontera **administrativa/de API** (RBAC, cuotas, nombres), no de red: dos Pods en namespaces distintos **se pueden pinguear libremente** salvo que agregues una NetworkPolicy. Si el TP quiere aislamiento real "estilo VLAN", tiene que ser vía NetworkPolicy (o, un nivel más abajo, redes Docker separadas por grupo de servicios).

### 8. Balanceo de carga: L4 (Service) vs. L7 (Ingress) — *Clase 5*
La Clase 5 distingue balanceo **a nivel IP, a nivel DNS, a nivel servicios (balanceadores) y a nivel objetos (CDN)**. En K8s:
- Un **Service ClusterIP/NodePort** balancea a **nivel IP:puerto (L4)** vía reglas de iptables/IPVS que arma `kube-proxy` — no mira HTTP, solo reparte conexiones TCP/UDP entre los Pods que matchean el selector.
- Un **Ingress** balancea a **nivel L7**, tipo los "balanceadores"/reverse-proxy de la Clase 5: puede rutear por hostname o por path HTTP hacia distintos microservicios (`/catalogo` → pod catálogo, `/checkout` → pod checkout), algo que un Service L4 no puede hacer.
Documentar esta diferencia (con qué protocolo/capa opera cada componente) es justo el tipo de precisión que pide la letra del TP.

### 9. ClusterIP como "anycast casero" — *Clase 5* (analogía, no es el mismo mecanismo)
La Clase 5 dice textualmente: *"se suele armar un cluster de servidores internos usando la misma tecnología de Anycast para la LAN"* — una **ClusterIP** de Kubernetes es conceptualmente lo mismo que un Anycast (**una IP virtual, muchos backends posibles, relación 1-a-muchos** en vez de unicast 1-a-1), aunque el mecanismo interno sea distinto: Anycast real se apoya en BGP/ECMP anunciando la misma ruta desde varios puntos de la red, mientras que una ClusterIP se resuelve con **DNAT local vía iptables/IPVS** en cada nodo, no con ruteo. Sirve como analogía para explicar la intención (alta disponibilidad, mismo "nombre" para múltiples instancias) dejando clara la diferencia de implementación si te preguntan "¿esto es anycast de verdad?" — la respuesta correcta es "no, es DNAT L4, pero cumple un rol parecido".

### 10. DNS jerárquico → CoreDNS del clúster — *Lab 1 (pregunta de resolución DNS), Clase 5*
El Lab 1 hace resolver a mano la cadena completa: navegador → hosts → resolver del ISP → root → NIC.AR → NS del dominio → NS del subdominio. Kubernetes tiene su propia jerarquía análoga con **CoreDNS**: un Pod resuelve `mi-servicio.mi-namespace.svc.cluster.local` mediante un `search domain` que el kubelet inyecta en `/etc/resolv.conf` del Pod, y CoreDNS resuelve `cluster.local` internamente (Service→ClusterIP) y reenvía (forward) lo que no es del dominio del clúster hacia el resolver del nodo/host — mismo patrón jerárquico "de lo específico a lo general" que en DNS de Internet, aplicado a la escala del clúster. Para el diagrama: aclarar que CoreDNS corre como Deployment (Pods) con su propia ClusterIP fija, típicamente `10.96.0.10`.

### 11. ARP y MetalLB en modo L2 — *Clase 2, Lab 1*
Un Kind puro (sin nada extra) no tiene forma nativa de dar un Service tipo **LoadBalancer** una IP "real" (eso lo resuelve la nube en EKS/GKE). La solución típica en laptop es **MetalLB en modo L2**: un Pod "speaker" en algún nodo empieza a responder **ARP** (o NDP en IPv6) por la IP virtual asignada al Service, igual que describe la Clase 2 sobre cómo un switch/host aprende y contesta en el dominio de broadcast — es el mismo mecanismo de ARP del Lab 1 (pregunta "qué protocolo se usa para resolver la MAC de un dispositivo local"), aplicado para que la red Docker/`kind` sepa a qué contenedor-nodo mandar los paquetes destinados a esa IP virtual. Importante: **MetalLB L2 requiere que la IP del pool esté en el mismo segmento L2** que los nodos (mismo bridge Docker) — otra razón concreta para documentar bien el bloque de red del bridge `kind` en el diagrama.

### 12. Encapsulamiento / overlay: MPLS y VPN como modelo mental de VXLAN — *Clase 4 (MPLS), Clase 6 (capas de VPN)*
Ningún PDF menciona VXLAN, pero el **patrón de encapsulamiento** que vas a necesitar explicar para el CNI (si el tráfico pod-a-pod entre nodos viaja encapsulado) es estructuralmente el mismo que:
- El header **MPLS** de la Clase 4: se le agrega una etiqueta/cabecera extra al paquete original y los nodos intermedios solo miran esa cabecera, no el contenido — la idea de "paquete dentro de otro paquete con su propio direccionamiento" es la misma que un **VXLAN** (Ethernet original del Pod, encapsulado en UDP entre las IP reales de los nodos).
- El diagrama de **"Capas de una VPN"** de la Clase 6 (`payload → túnel L2TP → UDP → IPSec → IPv4 → Ethernet`) es prácticamente el mismo dibujo que hay que hacer para VXLAN (`frame del Pod → header VXLAN → UDP → IP del nodo → Ethernet físico`).
Si tu CNI (kindnet/Flannel/Calico) usa modo **overlay** en vez de rutas directas ("host-gw"), aclará en el diagrama qué se encapsula y agregá el **overhead** que eso implica (típicamente 50 bytes extra con VXLAN) — la Clase 4/Clase 6 no hablan de MTU, así que esta parte es aporte tuyo, decilo así si te preguntan.

### 13. Ruteo estático vs. dinámico entre nodos — *Clase 3, Lab 5*
Cada nodo de Kubernetes necesita saber cómo llegar a los rangos de Pods **de los demás nodos**. Hay dos maneras, calcadas de la Clase 3:
- **Modo "ruteo estático"**: el CNI en modo *host-gw* instala, en la tabla de ruteo de cada nodo, una ruta fija por nodo destino (`10.244.1.0/24 vía <IP del nodo 1>`) — conceptualmente idéntico al `ip route <red> <máscara> <interfaz>` del Lab 5, solo que lo automatiza el CNI en vez de un humano.
- **Modo "ruteo dinámico"**: **Calico puede correr en modo BGP**, donde cada nodo es un **peer BGP** (típicamente con **ASN privado**) que anuncia su rango de Pods a los demás — es un uso real y directo de los conceptos de AS/iBGP/eBGP de la Clase 3, a escala de clúster en vez de a escala de Internet. Si tu CNI usa esto, es un lindísimo gancho para conectar la Clase 3/Lab 6 (BGP) con el TP.
En un clúster Kind de un solo laptop con **kindnet** (el CNI por defecto), en la práctica todos los nodos son contenedores en la **misma red Docker/L2**, así que puede no hacer falta ni ruteo ni overlay entre nodos (van directo por el bridge) — vale la pena confirmarlo con `ip route` adentro de un nodo y decirlo explícitamente en el documento en vez de asumir.

### 14. Spine/Leaf y tráfico East-West → tráfico entre microservicios — *Clase 2*
La Clase 2 contrasta el diseño **legacy** de datacenter (mayoría de tráfico **North/South**, cliente-servidor) contra el diseño **Spine/Leaf** (pensado para tráfico **East/West**, servidor-servidor). Una arquitectura de microservicios es, por definición, mayoritariamente tráfico **East/West** (Pod a Pod: frontend→catálogo, checkout→pagos, etc.), con solo una fracción **North/South** (usuario→Ingress). Es un buen argumento de diseño para el documento: explicar por qué el clúster necesita que la red entre nodos/Pods sea plana y de baja latencia, igual que un fabric Spine/Leaf, aunque acá esté simulado dentro de un solo host físico.

### 15. IP pública vs. privada, y quién te la asignó — *Clase 3 (IANA/LACNIC), Clase 5 (Carriers/ISP)*
Para justificar "por qué elegiste rangos privados" conviene apoyarse en la cadena de asignación real que ven en Clase 3/5: IANA delega en LACNIC (RIR de Latinoamérica), LACNIC delega en el ISP, el ISP le da (probablemente) una IP con **NAT/CGNAT** a tu router hogareño — vos **no sos dueño de ninguna IP pública**, por eso todo lo que corre en tu laptop (Docker, Kind, Pods, Services) usa exclusivamente rangos **privados no ruteables en Internet** (aunque el PDF no cite "RFC 1918" por número, es la convención de facto en todos los ejemplos de la cátedra — ver la nota de convenciones al principio de este documento).

### 16. Router vs. Switch L3 → kube-proxy / CNI haciendo de "router" del clúster — *Clase 2*
La Clase 2 remarca que un **Switch L3 no tiene puertos WAN** y rutea "por hardware" entre VLANs, mientras que un **Router** hace forwarding entre redes distintas "por software, muy flexible". El rol que cumple **kube-proxy** (o el componente equivalente del CNI) — decidir por iptables/IPVS a qué Pod mandar un paquete dirigido a una ClusterIP, o rutear entre el Pod CIDR y el Service CIDR — es exactamente ese rol de "router" hecho en software sobre un Linux genérico, no hardware dedicado. Útil para explicar, capa por capa, qué componente de tu arquitectura cumple el rol de cada dispositivo clásico (switch, router, firewall) que preguntarían en el oral.

### 17. Sistemas operativos y protocolos de cada capa (para completar el diagrama) — *transversal, aporte propio*
Esto no sale de los PDF (son detalles de Docker/Kind/Kubernetes) pero hace falta para que el diagrama cumpla con el requisito de "sistemas operativos" de la letra del TP:
- **Host físico**: laptop Linux (kernel con soporte de `network namespaces`, `veth`, `netfilter/iptables` o `nftables` — son la base sobre la que se construye *todo* el resto).
- **Nodos Kind**: son contenedores Docker corriendo la imagen `kindest/node`, basada en una distro Linux minimalista con **systemd + containerd + kubelet** adentro (un contenedor "haciendo de VM").
- **Pods/microservicios de "The Store"**: cada uno con su propia imagen base (Alpine/Debian-slim/distroless, según el microservicio) corriendo como proceso aislado por `namespaces` de Linux dentro del nodo.
Documentar esta cadena (host Linux → contenedor-nodo Linux → contenedor-pod Linux) es coherente con cómo la Clase 2 desglosa capas físicas/lógicas de una red real, aplicado a virtualización de SO en vez de cableado.

---

## Parte 3 — Preguntas probables de los profesores

Agrupadas por tema, en el estilo en que la cátedra insiste (les gusta pedir que **justifiques** cada elección, no solo que la muestres). Para cada una anoto de qué clase sacar la respuesta.

**Direccionamiento / CIDR** *(Lab 1, Clase 1, Clase 3)*
- ¿Por qué elegiste ese bloque/rango de IP para la red de Docker, para el Pod CIDR y para el Service CIDR?
- ¿Qué pasa si ese rango se superpone con la red de tu Wi-Fi/LAN de casa? ¿Y si se superpone entre sí el Pod CIDR y el Service CIDR?
- ¿Cuántos hosts/Pods entran en ese bloque? ¿Por qué elegiste ese tamaño de máscara y no uno más chico/grande?
- ¿Por qué usás rangos privados y no una IP pública para los Pods?
- Mostrame en la tabla de ruteo del host (o del nodo) cómo sabe el kernel a qué red mandar cada paquete.

**NAT** *(Clase 6)*
- ¿Qué tipo de NAT hace Docker (SNAT/DNAT)? ¿Es Full Cone, Restricted, Symmetric?
- ¿Cuántos "saltos" de NAT hay entre un Pod y, por ejemplo, `google.com`? Dibujalo.
- Si publicás un puerto con `hostPort` o `NodePort`, ¿qué tipo de NAT es eso?
- ¿Qué pasa si dos servicios necesitan iniciar conexión uno hacia el otro estando cada uno "adentro" de su propio NAT (ej. dos clústeres)? ¿Cómo resolverías eso (STUN/TURN/ICE, o simplemente no aplica en tu escenario)?
- NAT no es lo mismo en IPv4 que en IPv6: ¿tu diseño usa IPv6 en algún punto? ¿Por qué sí o por qué no?

**Capa 2 / Bridge / VLAN** *(Clase 2, Lab 4)*
- ¿Qué es, en términos de capa 2, la red que crea Docker? ¿Es un switch, un hub, un bridge?
- ¿Cuál es el dominio de broadcast en tu arquitectura? ¿Dónde "termina" el ARP y dónde empieza el ruteo L3?
- ¿Un Namespace de Kubernetes es lo mismo que una VLAN? Justificá la diferencia.
- Si tuvieras que aislar tráfico entre dos microservicios sin usar NetworkPolicies, ¿cómo lo harías con lo que viste en la materia (VLANs, redes Docker separadas)?

**DMZ / Seguridad perimetral** *(Clase 6)*
- ¿Dónde está la DMZ en tu arquitectura? ¿Qué componente cumple ese rol?
- Aplicá las 4 reglas de tráfico de DMZ (Internet↔DMZ↔interno) a tu diagrama concreto: ¿qué está permitido y qué bloqueado en cada dirección?
- ¿Tenés (o necesitarías) un Jump Server o bastion para administrar el clúster? ¿Por qué sí o por qué no en un entorno de laptop?
- Topología de 1 firewall vs. 2 firewalls: ¿cuál se parece más a tu diseño? ¿Por qué no usaste la otra?

**ACL / NetworkPolicy / Firewall** *(Clase 4, Clase 6)*
- ¿Cómo restringirías que el servicio de pagos no pueda ser contactado directamente por el servicio de catálogo?
- Una NetworkPolicy, ¿filtra en qué capa (2, 3, 4, 7)? ¿Por IP, por puerto, por ambos?
- ¿Kubernetes aísla el tráfico entre Pods por default? (Respuesta correcta: no — es la trampa más probable.)

**Ruteo** *(Clase 3, Lab 5, Lab 6)*
- El CNI que usa tu clúster, ¿hace ruteo estático o dinámico entre nodos?
- Si agregaras un segundo nodo worker, ¿quién actualiza las rutas para que un Pod de un nodo llegue a un Pod de otro nodo?
- ¿Alguno de tus componentes usa BGP? Si no, ¿cómo se comparan las alternativas (rutas estáticas vs. BGP tipo Calico) en términos de lo que viste en Clase 3?
- ¿Qué Distancia Administrativa tendría una ruta puesta a mano vs. una aprendida dinámicamente, si convivieran las dos?

**Balanceo de carga / DNS** *(Clase 5, Lab 1)*
- Tu Ingress, ¿balancea en capa 4 o capa 7? ¿Cómo decide a qué Pod mandar cada request?
- ¿Cómo resuelve un Pod el nombre de otro servicio del clúster? Segui la cadena completa como en el ejercicio de DNS del Lab 1.
- ¿Qué pasa si se cae CoreDNS?
- ¿Tu ClusterIP es "anycast"? ¿Es lo mismo que el Anycast de la Clase 5 o no? Justificá la diferencia de mecanismo.

**Encapsulamiento / overlay** *(Clase 4, Clase 6)*
- ¿Tu CNI encapsula el tráfico entre Pods (VXLAN/overlay) o rutea directo? ¿Cómo lo comprobaste?
- Si encapsula, ¿qué overhead agrega esa encapsulación? ¿Afecta el MTU efectivo?
- Compará el "solo miro la etiqueta, no el destino" de MPLS con lo que hace un túnel VXLAN.

**Física / enlaces / SO** *(Clase 1, Clase 2)*
- ¿Qué tipo de enlace físico conecta tu laptop a Internet (WiFi, qué estándar 802.11, o UTP)?
- Todo tu clúster corre en un solo host físico: ¿dónde están los puntos únicos de falla (SPOF)? (Gancho directo al Lab 2, ejercicio de ToR/SPOF.)
- ¿Qué sistema operativo corre en cada capa (host, nodo Kind, contenedor de cada microservicio)?

**Terraform / IaC (networking-adjacente)**
- ¿Cómo modela tu código Terraform estos recursos de red (`docker_network`, el clúster Kind, los CIDR)? ¿Están hardcodeados o son variables?
- Si corrés `terraform apply` dos veces, ¿es idempotente? ¿Qué pasaría si dos aplicaciones del mismo código generaran bloques que se solapan?
- ¿Qué pasa si el bloque que Terraform intenta crear ya está tomado por otra red Docker en tu laptop? ¿Cómo lo detectás/evitás?

---

*Fin del resumen. Las citas textuales entre comillas están tomadas literal de los slides (vía `pdftotext -layout`); todo lo de la Parte 2 y las sugerencias de valores por defecto de Kind/Kubernetes (Parte 2, puntos 1, 11, 12, 17) son conocimiento general de Kubernetes/Docker aportado para el TP, no contenido de los PDF — conviene verificarlos contra tu clúster real (`docker network inspect kind`, `kubectl cluster-info dump | grep -i cidr`, `ip route` dentro de un nodo) antes de ponerlos en el diagrama final.*
