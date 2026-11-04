#!/usr/bin/env python3
"""PPT editorial editable de The Store. Requiere python-pptx==1.0.2.

Solo genera documentos: no accede a AWS ni ejecuta Terraform.
La conversión a PDF se realiza por separado con LibreOffice.
"""
from pathlib import Path
import json

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "entrega"
OUT.mkdir(parents=True, exist_ok=True)
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333333), Inches(7.5)
prs.core_properties.title = "Infraestructura como código con Terraform — The Store"
prs.core_properties.subject = "72.20 Redes de Información · Grupo 2 · ITBA · 2C 2026"
prs.core_properties.author = "Matias Rossi; Juan Pablo Birsa; Federico Viera"
prs.core_properties.keywords = "Terraform, IaC, AWS, The Store, Grupo 2"
prs.core_properties.comments = "Presentación editorial; IA y anexos ocultos en el recorrido principal."

BG, INK, MUTED = "F6F3ED", "242321", "625F59"
PURPLE, PALE, LINE = "6945C3", "EAE3F5", "D8D2C8"
WHITE, GREEN, RED = "FFFFFF", "326E58", "A24742"
LIGHT_GREEN, LIGHT_RED = "E7EEE7", "F1E3DE"
SLIDES = []
BOUNDS = []
MAIN_NUMBER = 0
TIMES = {
    "portada": 20, "tienda": 20, "problema": 45, "solucion": 45,
    "ventajas_ejecucion": 65, "ventajas_control": 65, "ventajas_recursos": 65,
    "proveedores_declarativo": 50, "ciclo": 75, "estado_dependencias": 60,
}



ORAL_NOTES = {
    "portada": "Somos el Grupo 2. Vamos a mostrar cómo Terraform nos ayuda a crear y cambiar los recursos que necesita The Store. El objetivo es que operar la tienda sea más repetible, revisable y menos dependiente de tareas manuales.",
    "tienda": "El cliente ve una tienda: busca productos, arma un carrito y compra. Para que eso funcione hay varias piezas trabajando juntas. Nuestro proyecto se ocupa de los recursos que las sostienen y de cómo administrarlos cuando necesitamos hacer cambios.",
    "problema": "Poner la tienda en marcha es solo el comienzo. Después aparecen nuevas necesidades: preparar una prueba, publicar una mejora o responder a un problema. Si cada cambio depende de reconstruir pasos y recordar decisiones, el equipo pierde tiempo y aumenta el riesgo de equivocarse. Una configuración inesperada puede terminar afectando una compra. Necesitamos una forma compartida de saber qué tenemos y cómo cambiarlo.",
    "solucion": "La propuesta es dejar escrita la definición del entorno y usar un proceso común para administrarlo. Antes de cambiar algo, vemos qué va a pasar. Después decidimos si aplicarlo y comprobamos el resultado. Esa definición queda disponible para el equipo, con historial de modificaciones. Terraform es la herramienta que conecta lo que necesitamos con los recursos de la tienda y organiza las acciones para crearlos, cambiarlos o retirarlos.",
    "terraform": "Terraform toma una definición escrita de los recursos que necesitamos y calcula cómo llevarla a la práctica. Por ejemplo, la tienda requiere conectividad, servidores y servicios para guardar sus datos. En lugar de configurar cada pieza por separado, podemos administrar el conjunto con la misma herramienta. Nosotros seguimos decidiendo qué necesita la tienda y revisando los cambios; Terraform se encarga de organizar y ejecutar esas acciones.",
    "ventajas_ejecucion": "La primera ventaja es automatizar el trabajo repetitivo. Una definición puede coordinar la creación de varios recursos, sin configurar cada uno a mano. La segunda es repetir un estándar: las copias del entorno parten de reglas conocidas, con diferencias que elegimos de forma explícita. En The Store usamos la misma definición de aplicación para las dos copias de la tienda. Además, repetir el procedimiento busca mantener lo que definimos, sin volver a crear todo. Para una empresa esto significa menos tareas manuales y menos dependencia de cómo las recuerda cada persona.",
    "ventajas_control": "Los cambios quedan guardados con historial: podemos ver qué se modificó, quién lo hizo y qué versión se revisó. Las reglas de acceso también quedan escritas, de modo que el equipo puede examinarlas antes de aplicarlas. Y la definición funciona como una documentación que acompaña a la operación: describe cómo debería estar armado el entorno. Así podemos responder preguntas concretas sobre la tienda sin depender únicamente de la memoria de alguien o de un documento separado que quedó viejo.",
    "ventajas_recursos": "Poder crear y retirar un entorno con un proceso repetible permite usar recursos durante el tiempo en que hacen falta. Un espacio temporal de pruebas puede eliminarse al terminar, ayudando a evitar gasto ocioso. También podemos reutilizar un modelo y adaptarlo a otra necesidad, cambiando su tamaño o ubicación sin volver a definir cada componente. El valor está en aprovechar trabajo ya realizado. En nuestro laboratorio los recursos consumen presupuesto, por eso su retiro también forma parte del procedimiento. El ahorro concreto depende de cómo se utilicen y de qué recursos se conserven.",
    "ejemplo_entornos": "Pensemos en una empresa que quiere probar una mejora sin tocar la tienda que atiende clientes. Puede preparar un espacio separado a partir de un modelo común, adaptarlo para esa prueba y retirarlo cuando termina. Eso permite repetir una configuración conocida y evitar que cada equipo empiece desde cero. Es un ejemplo de adopción de Terraform tomado de las posibilidades que explica la clase. Nuestro proyecto reutiliza definiciones para dos copias de la tienda; crear ambientes separados de pruebas y operación sería una aplicación adicional.",
    "ejemplo_cambios": "Otra situación es reemplazar un recurso importante. Podemos definir que se prepare primero el nuevo y después se retire el anterior, para diseñar una transición ordenada. También podemos proteger recursos críticos para que la herramienta bloquee un intento de eliminarlos. Son decisiones que quedan escritas antes de hacer el cambio. El beneficio es tener protecciones y un procedimiento previsto, en lugar de decidir cada paso mientras operamos. Estas capacidades ayudan a diseñar los cambios; el equipo también tiene que comprobar que la tienda siga funcionando como espera.",
    "proveedores_declarativo": "La misma forma de trabajar puede aplicarse a distintos servicios de una empresa: recursos en la nube, equipos propios o servicios externos. Terraform se conecta con ellos para administrar los recursos que definimos. Eso permite conservar un proceso común de revisión y ejecución, aunque cambien las plataformas. En The Store lo usamos con los servicios de AWS y con el despliegue de la aplicación. Adaptar una solución a otro proveedor puede requerir cambios, pero el equipo conserva la herramienta y el método de trabajo.",
    "ciclo": "El proceso tiene cuatro operaciones principales. Primero preparamos la herramienta para trabajar. Después pedimos un plan: una vista previa de lo que se agregaría, cambiaría o eliminaría. Ese paso permite revisar el impacto sin ejecutar todavía esas acciones. Si el cambio es el que buscamos, lo aplicamos y comprobamos el resultado. Cuando un entorno deja de hacer falta, podemos retirar sus recursos con una revisión similar. Durante la demo vamos a usar estos nombres breves: init, plan, apply y destroy. Lo importante es la decisión que permite cada uno: preparar, revisar, hacer el cambio o retirar.",
    "estado_dependencias": "Para organizar los cambios, Terraform necesita saber qué recursos están bajo su administración y cómo se relacionan con nuestra definición. Mantiene un registro que el equipo puede compartir, para trabajar con una base común. También ordena las tareas: primero tiene que existir una red, después sus conexiones y luego los servidores que las usan. Así el operador no tiene que coordinar cada paso manualmente. En The Store ese registro se guarda de forma compartida y protegida. El equipo sigue revisando quién opera y qué cambios se aplican.",
    "arquitectura": "En nuestra solución el cliente entra por un punto común que reparte las solicitudes entre dos copias de la tienda. Cada copia corre en un servidor privado y ambas utilizan los mismos servicios de datos. Terraform administra los recursos que componen esa solución y los cambios sobre la aplicación. Las dos copias son independientes: una no aumenta los recursos de la otra. Este es el entorno sobre el que vamos a demostrar cómo detectamos una diferencia, ajustamos la configuración, cambiamos de versión y aislamos una parte cuando hace falta.",
    "cierre": "La propuesta es adoptar Terraform para automatizar tareas, repetir configuraciones conocidas y revisar los cambios antes de ejecutarlos. También nos permite conservar historial, expresar reglas de acceso y reutilizar un modelo para otras necesidades. La clase muestra que estas capacidades pueden servir para preparar pruebas, ampliar entornos y diseñar cambios con protecciones. Nuestro proyecto las conecta con una tienda concreta. El valor que buscamos es que operar y hacer cambios sea un proceso que el equipo pueda entender, repetir y comprobar.",
}


def rgb(value):
    return RGBColor.from_string(value)


def rect(s, x, y, w, h, fill=None, stroke=None, radius=False):
    shape = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                               Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shape.adjustments[0] = .08
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = rgb(fill)
    else:
        shape.fill.background()
    if stroke:
        shape.line.color.rgb = rgb(stroke)
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


def text(s, x, y, w, h, value, size=22, color=INK, bold=False,
         align=PP_ALIGN.LEFT, font="Arial", valign=MSO_ANCHOR.TOP):
    shape = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = valign
    for i, line in enumerate(value.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.alignment = align
        p.space_before = p.space_after = Pt(0)
        p.line_spacing = 1.1
        p.font.name = font
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = rgb(color)
    BOUNDS.append((len(prs.slides), x, y, w, h, value))
    return shape


def line(s, x1, y1, x2, y2, color=LINE, width=1.2, arrow=False):
    sh = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                              Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    sh.line.color.rgb = rgb(color)
    sh.line.width = Pt(width)
    if arrow:
        end = OxmlElement("a:tailEnd")
        end.set("type", "triangle")
        sh.line._get_or_add_ln().append(end)
    return sh


def dot(s, x, y, d=.14, color=PURPLE):
    sh = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    sh.fill.solid()
    sh.fill.fore_color.rgb = rgb(color)
    sh.line.fill.background()
    return sh


def tag(s, x, y, value, w=1.45, fill=PALE, color=PURPLE):
    rect(s, x, y, w, .34, fill)
    text(s, x + .10, y + .065, w - .20, .21, value, 11, color, True)


def base(section, title, number=None, bg=BG, hidden=False):
    global MAIN_NUMBER
    if not hidden:
        MAIN_NUMBER += 1
        number = f"{MAIN_NUMBER:02}"
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb(bg)
    if hidden:
        s._element.set("show", "0")
    rect(s, .77, .47, .46, .045, PURPLE)
    text(s, .77, .69, 11.8, .25, section.upper(), 11.5, PURPLE, True)
    if title:
        text(s, .77, 1.14, 11.8, 1.03, title, 33, INK, True)
    line(s, .77, 6.93, 12.56, 6.93, LINE, .7)
    text(s, .77, 7.08, 10.5, .18, "THE STORE  /  TERRAFORM      ·      REDES DE INFORMACIÓN  /  GRUPO 2", 9.5, MUTED)
    if number:
        text(s, 11.7, 7.05, .85, .24, number, 11, PURPLE, True, PP_ALIGN.RIGHT)
    return s


def takeaway(s, value, y=6.18, color=PURPLE, size=20):
    line(s, .79, y, .79, y + .42, PURPLE, 2.2)
    text(s, 1.02, y + .015, 11.35, .54, value, size, color)


def note(s, key, title, seconds, speaker, script, demo="", transition="", hidden=False, sources=()):
    seconds = TIMES.get(key, seconds)
    technical_support = script if key in ORAL_NOTES else ""
    script = ORAL_NOTES.get(key, script)
    chunks = [title, f"Tiempo objetivo: {seconds} s · Orador sugerido: {speaker}",
              "PROPÓSITO Y GUION\n" + script]
    if demo:
        chunks.append("OPERADOR / DEMO\n" + demo)
    if transition:
        chunks.append("TRANSICIÓN\n" + transition)
    if technical_support:
        chunks.append("RESPALDO PARA PREGUNTAS (NO LEER COMO GUION)\n" + technical_support)
    if sources:
        chunks.append("FUENTES\n" + "\n".join(sources))
    s.notes_slide.notes_text_frame.text = "\n\n".join(chunks)
    SLIDES.append(dict(physical=len(prs.slides), key=key, title=title, seconds=seconds,
                       speaker=speaker, hidden=hidden, script=script, technical_support=technical_support, demo=demo,
                       transition=transition, sources=list(sources)))


def col(s, x, y, num, heading, body, w=3.55):
    text(s, x, y, w, .55, num, 31, PURPLE, True)
    line(s, x, y + .76, x + w, y + .76)
    text(s, x, y + 1.02, w, .85, heading, 25, INK, True)
    text(s, x, y + 2.03, w, 1.12, body, 20, MUTED)


# 01 — Carátula: datos exactos del PDF vigente.
s = base("ITBA · 72.20 Redes de Información", "", "01")
text(s, .77, 1.42, 10.9, 1.9, "Infraestructura\ncomo código", 49, INK, True)
# El acento tiene su propio objeto editable.
text(s, .77, 3.08, 10.9, .94, "con Terraform.", 49, PURPLE, True)
text(s, .8, 4.46, 10.6, .66, "The Store en AWS\nTrabajo Práctico Especial · Tema 1", 23, MUTED)
text(s, .8, 5.77, 7.5, .86, "Matias Rossi · 63202\nJuan Pablo Birsa · 64500\nFederico Viera · 62022", 17, INK)
text(s, 9.15, 5.8, 3.38, .77, "GRUPO 2\n2.º cuatrimestre · 2026", 16, MUTED, False, PP_ALIGN.RIGHT)
note(s, "portada", "Infraestructura como código con Terraform", 30, "Matias",
     "Presentar al grupo y el tema. Nuestro trabajo toma The Store, una tienda online de cinco microservicios, "
     "y usa Terraform para administrar la infraestructura que la sostiene en AWS. La pregunta que organiza la charla es "
     "cómo repetir un entorno y hacer cambios con control. Vamos a mostrar el problema, la propuesta y la herramienta; "
     "después haremos cuatro cambios sobre la tienda en vivo. No prometer cifras de ahorro ni disponibilidad que no hayamos medido.",
     transition="Para entender por qué esto importa, primero veamos qué necesita una compra.",
     sources=("Pre Entrega - Grupo 2 -1.pdf · carátula y secciones 1–3",))

# 02 — Contexto sin catálogo de tecnologías.
s = base("El negocio", "Una compra depende de varias piezas", "02")
text(s, .8, 2.33, 10.7, .85, "El cliente ve una tienda.\nEl equipo coordina varias piezas.", 27, INK)
steps = [("01", "Ver productos", "Información de productos"), ("02", "Armar el carrito", "Selección del cliente"),
         ("03", "Comprar", "Registro de la compra")]
for i, (n, title, body) in enumerate(steps):
    x = .8 + i * 4.18
    line(s, x, 3.68, x + 3.35, 3.68, PURPLE, 2)
    text(s, x, 3.94, 3.45, .38, n, 17, PURPLE, True)
    text(s, x, 4.45, 3.6, .7, title, 26, INK, True)
    text(s, x, 5.25, 3.3, .5, body, 20, MUTED)
takeaway(s, "Para vender, la aplicación y su infraestructura tienen que trabajar juntas.")
note(s, "tienda", "Una compra depende de varias piezas", 30, "Matias",
     "The Store permite recorrer un catálogo, armar un carrito y confirmar una compra. La UI es la cara visible. "
     "Por detrás colaboran Catalog, Cart, Checkout y Orders. Separar estas responsabilidades permite cambiar cada servicio, "
     "pero también exige coordinar conexiones, despliegues y datos. En el punto de partida, un script arma el entorno local "
     "y los servicios usan almacenamiento en memoria. Nuestra propuesta lleva la operación a AWS y conecta persistencias administradas. "
     "No hace falta describir los lenguajes ni los puertos para entender la necesidad de administrar el conjunto.",
     transition="El desafío no termina cuando conseguimos que la tienda arranque.",
     sources=("Preentrega vigente · secciones 1–2",))

# 03 — Vender el problema a partir del contexto real.
s = base("El problema", "Una tienda online necesita cambios bajo control", "03")
text(s, .8, 2.29, 11.3, .65, "Cada cambio puede afectar la operación y las compras de los clientes.", 23, MUTED)
rows = [("Repetir un entorno", "Volver a coordinar recursos y dependencias."),
        ("Entender qué cambió", "Detectar diferencias respecto de la configuración acordada."),
        ("Contener un incidente", "Actuar con un procedimiento que podamos revisar y repetir.")]
for i, (a, b) in enumerate(rows):
    y = 3.18 + i * .91
    text(s, .8, y, .5, .4, f"0{i+1}", 17, PURPLE, True)
    text(s, 1.49, y, 4.05, .62, a, 24, INK, True)
    text(s, 6.08, y + .02, 6.0, .65, b, 21, MUTED)
    line(s, 1.49, y + .70, 12.48, y + .70)
takeaway(s, "Un cambio difícil de rastrear puede terminar en una compra interrumpida.", size=21)
note(s, "problema", "Una tienda online necesita cambios bajo control", 60, "Matias",
     "No partimos de una aplicación que nadie puede ejecutar: ya existe local.sh. Ese script automatiza pasos para crear kind, "
     "construir imágenes y aplicar objetos. El problema es que esa secuencia no describe de manera unificada el resultado esperado "
     "ni mantiene el inventario y el plan de cambios que necesitamos para gestionar la infraestructura. Al crecer el entorno, "
     "reproducirlo y modificarlo exige más coordinación. Una configuración cambiada desde la consola puede quedar fuera de lo acordado. "
     "Y ante un incidente hay que reconstruir qué existe y qué debería existir antes de decidir cómo actuar. "
     "Desde la perspectiva de quien financia el proyecto, esto significa tiempo operativo, incertidumbre y exposición a errores. "
     "Son riesgos del enfoque, no estadísticas de incidentes que hayamos medido en la tienda. "
     "La inversión que proponemos apunta a que el conocimiento del entorno quede escrito y a que los cambios sean revisables por el equipo.",
     transition="Nuestra solución comienza por cambiar la forma de definir y modificar ese entorno.",
     sources=("Preentrega vigente · sección 1",))

# 04 — Antes y después de la propuesta.
s = base("La solución", "Terraform para crear, cambiar y retirar con control", "04")
rect(s, .8, 2.43, 5.57, 3.15, "EDE8DF")
rect(s, 6.78, 2.43, 5.75, 3.15, PALE)
text(s, 1.07, 2.71, 4.9, .34, "PUNTO DE PARTIDA", 12, MUTED, True)
text(s, 7.05, 2.71, 5.0, .34, "NUESTRA PROPUESTA", 12, PURPLE, True)
for i, value in enumerate(["Ejecutar una secuencia de pasos", "Comprobar recién al terminar", "Reconstruir cómo quedó el entorno"]):
    text(s, 1.07, 3.33 + i * .66, 4.98, .58, value, 22)
for i, value in enumerate(["Definir qué queremos tener", "Ver los cambios antes de hacerlos", "Mantener registro de los recursos"]):
    text(s, 7.05, 3.33 + i * .66, 5.05, .58, value, 22)
takeaway(s, "Infraestructura como código (IaC): una definición compartida del entorno.", size=21)
note(s, "solucion", "Terraform para crear, cambiar y retirar con control", 60, "Matias",
     "Proponemos administrar el entorno como una configuración versionada. El equipo define qué necesita la tienda: red, "
     "cómputo, balanceador, datos y despliegues. Esa definición puede revisarse en Git y usarse para recrear recursos. "
     "Antes de tocar el entorno se calcula una propuesta de cambios. Después se aplica y se comprueba el resultado. "
     "El estado vincula la configuración con los recursos que administra la herramienta. "
     "La solución concreta de nuestro grupo usa Terraform en AWS y administra también los objetos de los dos clústeres kind. "
     "Esto no elimina la necesidad de probar ni decide por nosotros si una modificación conviene. Nos da una base común "
     "para entender y ejecutar los cambios. El valor es que otra persona del equipo pueda revisar y repetir el procedimiento.",
     transition="La herramienta que elegimos para hacerlo es Terraform.",
     sources=("Preentrega vigente · secciones 1–3", "https://developer.hashicorp.com/terraform/intro"))

# 05 — Definición de la tecnología protagonista.
s = base("La tecnología", "Terraform crea y actualiza los recursos de la tienda", "05")
text(s, .8, 2.29, 11.4, .78, "Definimos qué necesitamos; Terraform organiza los cambios.", 28)
nodes = [(.8, 3.64, 3.30, "Definición", "Qué recursos necesitamos"),
         (5.05, 3.64, 3.0, "Terraform", "Calcula y ejecuta cambios"),
         (9.04, 3.64, 3.49, "Recursos", "Red, servidores y datos")]
for x, y, w, a, b in nodes:
    rect(s, x, y, w, 1.55, PALE if a == "Terraform" else WHITE, LINE if a != "Terraform" else None)
    text(s, x + .19, y + .26, w - .38, .52, a, 23, PURPLE if a == "Terraform" else INK, True, PP_ALIGN.CENTER)
    text(s, x + .18, y + .91, w - .36, .45, b, 16.5, MUTED, align=PP_ALIGN.CENTER)
line(s, 4.2, 4.4, 4.89, 4.4, PURPLE, 1.8, True)
line(s, 8.18, 4.4, 8.88, 4.4, PURPLE, 1.8, True)
takeaway(s, "Declaramos qué debe existir; Terraform calcula cómo alcanzar esa configuración.", size=20)
note(s, "terraform", "Terraform crea y actualiza los recursos de la tienda", 45, "Juan Pablo",
     "Terraform es una herramienta de infraestructura como código de HashiCorp. Definimos recursos en archivos legibles, "
     "en un lenguaje declarativo llamado HCL. Declarativo significa expresar el resultado deseado, por ejemplo una red y "
     "dos máquinas, en lugar de escribir cada clic que haríamos en una consola. Terraform se comunica con las APIs mediante "
     "providers. En este proyecto utilizamos AWS para la infraestructura y Kubernetes para objetos de aplicación. "
     "Los módulos agrupan recursos relacionados. La herramienta calcula dependencias y acciones; el equipo sigue siendo "
     "responsable de elegir la arquitectura, revisar el plan y validar el funcionamiento. Docker y kind se preparan mediante "
     "el bootstrap automatizado de las EC2. Terraform administra esos recursos y su configuración; no reemplaza toda tarea operativa.",
     transition="Primero veamos qué gana el equipo al adoptar este enfoque.",
     sources=("https://developer.hashicorp.com/terraform/intro", "README y terraform/main.tf · configuración actual"))

# 06 — Ventajas IaC 1 y 2: velocidad y consistencia.
s = base("Ventajas de IaC · ejecución", "Crear más rápido y repetir el mismo estándar", "06")
text(s, .8, 2.37, 5.5, .65, "Automatización y velocidad", 25, PURPLE, True)
text(s, .8, 3.19, 5.35, 1.0, "Una configuración coordina\nla creación de los recursos.", 25, INK)
for i, value in enumerate(["Red", "Servidores", "Datos"]):
    x = .8 + i * 1.86
    rect(s, x, 4.68, 1.54, .7, WHITE, LINE)
    text(s, x + .12, 4.89, 1.30, .3, value, 18, align=PP_ALIGN.CENTER)
line(s, 6.55, 2.42, 6.55, 5.58, LINE)
text(s, 7.0, 2.37, 5.5, .85, "Consistencia y\nestandarización", 25, PURPLE, True)
text(s, 7.0, 3.64, 5.35, .83, "Mismas reglas,\nparámetros explícitos.", 25)
for x, value in [(7.0, "Copia A"), (9.92, "Copia B")]:
    rect(s, x, 4.68, 2.60, .7, PALE)
    text(s, x + .16, 4.89, 2.28, .3, value, 18, PURPLE, True, PP_ALIGN.CENTER)
takeaway(s, "Al repetir la misma definición, mantenemos lo acordado sin volver a crear todo.", size=19)
note(s, "ventajas_ejecucion", "Crear más rápido y repetir el mismo estándar", 75, "Juan Pablo",
     "Estas son dos razones para adoptar infraestructura como código. Automatización y velocidad: una configuración "
     "permite crear recursos relacionados sin configurar cada uno a mano. En The Store esto abarca VPC, subredes, "
     "EC2, balanceador y datos. Terraform resuelve sus operaciones y podemos repetir el procedimiento. La velocidad "
     "proviene de reducir tareas manuales; no mostramos un tiempo de creación que no hayamos medido. Consistencia "
     "y estandarización: el mismo módulo de aplicación se utiliza en los dos kind, con parámetros conocidos. También "
     "podemos reutilizar definiciones entre entornos, reduciendo diferencias como un Security Group inesperado en "
     "testing. Es una capacidad de adopción, no la afirmación de que el POC tenga ambientes de testing y producción. "
     "La clase agrega idempotencia: con el estado conservado y sin desvíos, repetir la misma definición busca mantener el mismo resultado, sin duplicar recursos. Para la organización, el beneficio es menos trabajo repetitivo y una base común para operar.",
     transition="Además de ejecutar, necesitamos saber qué se cambia y poder revisar sus reglas.",
     sources=("Clase 82.08 Cloud Computing · pp. 7–8 · ventajas IaC 1 y 2", "terraform/main.tf · app_a y app_b"))

# 07 — Ventajas IaC 3, 6 y 7: gobierno del cambio.
s = base("Ventajas de IaC · control", "Cada cambio se puede revisar, auditar y entender", "07")
governance = [(.8, "Control de\nversiones", "Historial de cambios", "Qué cambió, quién lo cambió\ny qué versión se aprobó."),
              (4.94, "Mejora en\nla seguridad", "Reglas de acceso", "Podemos revisar quién accede\na cada recurso y servicio."),
              (9.08, "Documentación\nviva", "Definición del entorno", "El código describe cómo\ndebería estar la infraestructura.")]
for x, heading, label, body in governance:
    text(s, x, 2.48, 3.45, .96, heading, 25, PURPLE, True)
    line(s, x, 3.72, x + 3.45, 3.72)
    text(s, x, 4.05, 3.45, .64, label, 21, INK, True)
    text(s, x, 4.91, 3.45, .97, body, 19, MUTED)
takeaway(s, "En The Store: conservamos el historial de la configuración y las reglas de acceso.", size=19)
note(s, "ventajas_control", "Cada cambio se puede revisar, auditar y entender", 75, "Juan Pablo",
     "Control de versiones: al guardar la configuración en Git tenemos historial de cambios, autores y revisiones. "
     "Podemos recuperar una definición anterior y evaluar su plan antes de aplicarla. Git aporta esa trazabilidad; "
     "Terraform ejecuta el cambio. Mejora en la seguridad: las reglas de acceso y las políticas quedan escritas. En "
     "The Store se ven en Security Groups y NetworkPolicies. Eso permite revisión por pares y análisis con herramientas "
     "automáticas; no atribuimos a Terraform un escáner incorporado ni afirmamos que este POC ya tenga ese análisis "
     "automatizado. Documentación viva: el código expresa el estado esperado del entorno y se modifica junto con el "
     "cambio, reduciendo la dependencia de un documento separado. El entorno real se contrasta con plan. Recuperar "
     "una configuración anterior exige revisar sus efectos; el historial de Git no es un respaldo de las bases.",
     transition="El valor también se refleja en cómo usamos los recursos y reutilizamos las configuraciones.",
     sources=("Clase 82.08 Cloud Computing · pp. 7–8 · ventajas IaC 3, 6 y 7", "Guía de políticas del proyecto"))

# 08 — Ventajas IaC 4 y 5: recursos y reutilización.
s = base("Ventajas de IaC · inversión", "Entornos temporales, soluciones reutilizables", "08")
text(s, .8, 2.38, 5.5, .6, "Reducción de costos", 25, PURPLE, True)
text(s, .8, 3.24, 5.4, .95, "Crear → Probar → Retirar", 25, INK, True)
text(s, .8, 4.46, 5.35, 1.10, "Eliminar entornos temporales\nayuda a evitar gasto ocioso.", 23, MUTED)
line(s, 6.55, 2.42, 6.55, 5.63, LINE)
text(s, 7.0, 2.38, 5.5, .85, "Crecer y reutilizar", 25, PURPLE, True)
text(s, 7.0, 3.69, 5.35, .75, "Un modelo que se adapta", 25, INK, True)
text(s, 7.0, 4.73, 5.35, 1.03, "Cambiar tamaño o ubicación\nsin volver a definir todo.", 23, MUTED)
takeaway(s, "En The Store: definiciones reutilizables y recursos que podemos retirar.", size=19)
note(s, "ventajas_recursos", "Entornos temporales, soluciones reutilizables", 75, "Juan Pablo",
     'Crear y retirar entornos temporales ayuda a evitar gasto ocioso. El proyecto opera con una sola configuración y un backend S3. Revisar destroy y auditar después: se retiran los recursos gestionados, incluidos datos según el plan; el bucket y los roles preexistentes se conservan fuera de esta configuración. Los módulos encapsulan configuraciones y parámetros; aplicación se utiliza dos veces, una por kind. UI 2→4 no agrega EC2 ni CPU/memoria física. El ahorro real depende de recursos, uso y duración.',
     transition="Por ejemplo, una empresa puede abrir un espacio de pruebas desde un modelo común.",
     sources=("Clase 82.08 Cloud Computing · pp. 7–8 · ventajas IaC 4 y 5", "https://developer.hashicorp.com/terraform/language/modules", "README vigente · ciclo de vida del entorno"))

# Aplicación empresarial: separar pruebas y operación mediante un modelo común.
s = base("Ejemplos de adopción · nuevos entornos", "Probar cambios sin tocar la tienda en operación", "09")
rect(s, .8, 3.40, 3.52, 1.33, PALE)
text(s, 1.02, 3.67, 3.08, .49, "Un mismo modelo", 25, PURPLE, True)
text(s, 1.02, 4.31, 3.08, .30, "Ajustado a cada necesidad", 15, MUTED)
for y, heading, body in [(2.55, "Espacio de pruebas", "Probar el cambio por separado."),
                          (4.38, "Tienda en operación", "Continuar atendiendo clientes.")]:
    rect(s, 7.02, y, 5.48, 1.26, WHITE, LINE)
    text(s, 7.24, y + .20, 5.04, .47, heading, 24, INK, True)
    text(s, 7.24, y + .80, 5.04, .34, body, 18, MUTED)
line(s, 4.42, 4.08, 5.48, 4.08, PURPLE, 1.5)
line(s, 5.48, 3.17, 5.48, 5.01, PURPLE, 1.5)
line(s, 5.48, 3.17, 6.84, 3.17, PURPLE, 1.5, True)
line(s, 5.48, 5.01, 6.84, 5.01, PURPLE, 1.5, True)
takeaway(s, "Termina la prueba: retiramos ese entorno temporal y sus recursos.", size=21)
note(s, "ejemplo_entornos", "Probar cambios sin tocar la tienda en operación", 60, "Juan Pablo",
     "Ejemplo de adopción empresarial derivado de la clase: antes de lanzar un cambio necesitamos probarlo sin "
     "afectar la tienda que atiende clientes. Un modelo reutilizable permite preparar un espacio separado y "
     "adaptar sus nombres, tamaños y ubicación mediante parámetros. Al terminar, retiramos los recursos temporales. "
     "El valor combina repetibilidad, menos trabajo manual y control del gasto. Técnicamente, la clase lo conecta "
     "con variables, módulos y blueprints. Nuestro POC reutiliza el módulo de aplicación en dos copias, pero esas "
     "copias sirven la misma tienda y comparten datos: no son ambientes separados de pruebas y producción. "
     "El ejemplo empresarial requeriría aislar sus recursos y datos. No atribuir al grupo una implementación de "
     "CI/CD o de entornos de producción que no existe.",
     transition="Otra situación es cambiar un recurso importante con un orden y unas protecciones definidos.",
     sources=("Clase 82.08 Cloud Computing · 10-IaC_Terraform · pp. 3, 24–25 y 31–32", "https://developer.hashicorp.com/terraform/language/modules"))

# Aplicación empresarial: ciclo de vida explicado mediante decisiones, sin sintaxis.
s = base("Ejemplos de adopción · cambios", "Cambiar recursos con menos riesgo operativo", "10")
text(s, .8, 2.37, 5.5, .85, "Preparar el reemplazo", 25, PURPLE, True)
for i, value in enumerate(["Actual", "Ambos", "Nuevo"]):
    x = .8 + 1.86 * i
    rect(s, x, 3.48, 1.52, .72, PALE if i == 1 else WHITE, None if i == 1 else LINE)
    text(s, x + .12, 3.70, 1.28, .31, value, 18, PURPLE if i == 1 else INK, True, PP_ALIGN.CENTER)
    if i < 2:
        line(s, x + 1.57, 3.85, x + 1.77, 3.85, PURPLE, 1.2, True)
text(s, .8, 4.66, 5.35, .93, "Crear el nuevo recurso\nantes de retirar el anterior.", 23)
line(s, 6.55, 2.42, 6.55, 5.65, LINE)
text(s, 7.0, 2.37, 5.5, .85, "Proteger recursos críticos", 25, PURPLE, True)
rect(s, 7.0, 3.48, 5.5, .72, PALE)
text(s, 7.20, 3.70, 5.1, .31, "Recurso protegido frente a bajas", 19, PURPLE, True)
text(s, 7.0, 4.66, 5.35, 1.05, "Bloquear una eliminación\nde un recurso protegido.", 23)
takeaway(s, "Podemos definir cómo reemplazar un recurso y cuándo bloquear su eliminación.", size=20)
note(s, "ejemplo_cambios", "Cambiar recursos con menos riesgo operativo", 60, "Juan Pablo",
     "Ejemplo de adopción empresarial de la clase: al reemplazar un servidor podemos pedir que se cree primero "
     "el nuevo recurso y se retire después el anterior. Eso da una base para diseñar una transición controlada. "
     "También podemos proteger recursos críticos para que Terraform rechace un plan que intente destruirlos. "
     "El valor es expresar estas decisiones antes de operar. En Terraform son create_before_destroy y prevent_destroy, "
     "reglas que la clase explica en la página 30. No hace falta pronunciar su sintaxis en la exposición. "
     "Son capacidades del producto y no nuevas pruebas del POC. El orden de creación no garantiza continuidad "
     "del servicio: salud, tráfico y capacidad deben resolverse en el diseño. La protección de bajas requiere "
     "mantener la regla en la configuración; no es un backup ni evita cualquier pérdida de datos. "
     "Terraform también puede modificar recursos existentes: el enfoque inmutable se elige donde corresponde.",
     transition="Estas decisiones pueden usar el mismo proceso aunque cambien los servicios que administramos.",
     sources=("Clase 82.08 Cloud Computing · 10-IaC_Terraform · pp. 4 y 30", "https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle"))

# 11 — Características Terraform: declarativo y múltiples proveedores.
s = base("Qué ofrece Terraform", "Una herramienta para distintos servicios", "09")
text(s, .8, 2.38, 5.15, .50, "Definir el resultado", 25, PURPLE, True)
text(s, .8, 3.12, 4.8, 1.12, "Decimos qué queremos\ntener.", 28, INK, True)
text(s, .8, 4.73, 4.4, 1.04, "Terraform calcula las operaciones\npara alcanzar esa definición.", 21, MUTED)
rect(s, 5.38, 3.40, 2.65, 1.24, PALE)
text(s, 5.58, 3.82, 2.25, .49, "Terraform", 25, PURPLE, True, PP_ALIGN.CENTER)
text(s, 9.13, 2.38, 3.4, .45, "Múltiples proveedores", 22, PURPLE, True)
for i, (label, value) in enumerate([("EN LA NUBE", "AWS · Azure · GCP"),
                                    ("EN EQUIPOS PROPIOS", "VMware"),
                                    ("EN SERVICIOS EXTERNOS", "GitHub · Datadog")]):
    y = 3.10 + i * .84
    text(s, 9.13, y, 3.38, .23, label, 10.5, PURPLE, True)
    text(s, 9.13, y + .30, 3.38, .38, value, 18)
line(s, 8.13, 4.02, 8.88, 4.02, PURPLE, 1.5, True)
takeaway(s, "En The Store: un mismo proceso administra los recursos y el despliegue de la tienda.", size=20)
note(s, "proveedores_declarativo", "Una herramienta para distintos servicios", 60, "Juan Pablo",
     "Terraform usa providers para comunicarse con las APIs de plataformas y servicios. Existen providers para AWS, "
     "Azure, GCP y Kubernetes, entre otros. El equipo conserva una herramienta y un flujo de trabajo comunes aunque "
     "gestione distintos servicios. También puede administrar servicios en equipos propios y SaaS, como VMware, GitHub y Datadog. En el POC se usan AWS y Kubernetes; los demás ejemplos muestran el alcance del "
     "producto, no despliegues realizados por nosotros. El enfoque es declarativo: expresamos los recursos y sus "
     "relaciones, y Terraform calcula las acciones. Un provider diferente puede requerir recursos y configuración "
     "diferentes; no se debe prometer mover la solución entre nubes sin adaptación. La capacidad valiosa es mantener "
     "el proceso de definición, revisión y aplicación en la misma herramienta.",
     transition="Antes de ejecutar esas acciones, podemos examinar su impacto con plan.",
     sources=("Clase 82.08 Cloud Computing · p. 14 · características Terraform", "https://developer.hashicorp.com/terraform/intro"))

# 10 — Operaciones principales, sin bloques de código.
s = base("Cómo funciona", "Revisar antes de cambiar", "10")
ops = [("01", "Preparar", "init", "Preparar la herramienta\npara trabajar."),
       ("02", "Revisar", "plan", "Ver lo que se agrega,\ncambia o elimina."),
       ("03", "Aplicar", "apply", "Hacer los cambios\nque revisamos."),
       ("04", "Retirar", "destroy", "Retirar los recursos\nque dejamos de usar.")]
rect(s, 3.82, 2.37, 2.91, 3.43, PALE)
for i, (n, a, cmd, b) in enumerate(ops):
    x = .8 + i * 3.16
    text(s, x, 2.54, 2.73, .45, n, 24, PURPLE, True)
    line(s, x, 3.11, x + 2.62, 3.11, PURPLE, 1.4)
    text(s, x, 3.4, 2.75, .55, a, 27, INK, True)
    text(s, x, 4.05, 2.73, .36, cmd, 18, PURPLE, font="Consolas")
    text(s, x, 4.76, 2.76, .95, b, 19, MUTED)
takeaway(s, "Primero vemos el impacto del cambio. Después decidimos aplicarlo.", size=20)
note(s, "ciclo", "Revisar antes de cambiar", 90, "Juan Pablo",
     'init prepara la raíz terraform/, descarga providers y conecta el backend S3. plan consulta y propone cambios; apply ejecuta un plan guardado o calcula otro si no se proporciona. destroy elimina los recursos administrados por esa configuración, tras revisar el alcance. El proyecto actual usa una sola raíz y un solo estado S3 con cifrado, versionado y bloqueo nativo. scripts/acceso-kind.sh se invoca desde Terraform para preparar el acceso a ambos kind. Tras cada caso se comprueban la tienda, ambas copias y la convergencia de configuración. Ninguna de esas verificaciones se ejecuta al generar este documento.',
     transition="Para calcular y ordenar estos cambios, Terraform utiliza estado y dependencias.",
     sources=("https://developer.hashicorp.com/terraform/cli/commands/plan", "https://developer.hashicorp.com/terraform/cli/commands/apply", "https://developer.hashicorp.com/terraform/cli/commands/destroy", "https://developer.hashicorp.com/terraform/cli/state"))

# 11 — Características Terraform: estado y dependencias.
s = base("Qué ofrece Terraform", "Saber qué existe y en qué orden cambiarlo", "11")
text(s, .8, 2.37, 5.5, .58, "Un registro compartido", 25, PURPLE, True)
text(s, .8, 3.16, 5.37, .85, "El equipo ve qué recursos\nestán bajo administración.", 24)
for i, (left, right) in enumerate([("Definición de red", "Red en AWS"), ("Servidor definido", "Servidor creado")]):
    y = 4.45 + i * .67
    text(s, .8, y, 2.65, .39, left, 18, INK, True)
    text(s, 3.38, y - .02, .5, .43, "↔", 21, PURPLE, True)
    text(s, 4.10, y, 2.04, .39, right, 18)
line(s, 6.55, 2.42, 6.55, 5.67, LINE)
text(s, 7.0, 2.37, 5.5, .9, "Ordenar las tareas", 25, PURPLE, True)
for i, value in enumerate(["Crear la red", "Preparar conexiones", "Crear servidores"]):
    y = 3.77 + i * .69
    rect(s, 8.1, y, 3.28, .44, PALE)
    text(s, 8.27, y + .10, 2.94, .26, value, 17, PURPLE, True, PP_ALIGN.CENTER)
    if i < 2:
        line(s, 9.74, y + .47, 9.74, y + .63, PURPLE, 1.2, True)
takeaway(s, "Una base compartida ayuda a coordinar al equipo y ordenar cada operación.", size=20)
note(s, "estado_dependencias", "Saber qué existe y en qué orden cambiarlo", 75, "Juan Pablo",
     'El estado vincula las direcciones de configuración con los recursos administrados. En el repo actual hay una sola configuración terraform/ y un backend S3 cifrado y con bloqueo nativo; el bucket tiene versionado según la preparación del README. Las referencias y depends_on expresan el orden entre módulos y recursos. El estado y su historial no son backups de la aplicación ni de las bases. El equipo debe coordinar operadores y verificar los resultados.',
     transition="Estas capacidades se concretan en la arquitectura de nuestra tienda.",
     sources=("Clase 82.08 Cloud Computing · p. 14 · características Terraform", "https://developer.hashicorp.com/terraform/language/state/purpose", "https://developer.hashicorp.com/terraform/internals/graph", "terraform/providers.tf · backend remoto"))

# 12 — Arquitectura simplificada y fiel al alcance vigente.
s = base("Nuestra implementación", "Una tienda, dos copias y datos compartidos", "12")
rect(s, 2.56, 2.27, 9.97, 3.67, None, LINE)
tag(s, 2.77, 2.10, "En la nube · AWS", 1.72, BG)
rect(s, .8, 3.48, 1.35, 1.0, WHITE, LINE)
text(s, .91, 3.81, 1.13, .38, "Cliente", 19, INK, True, PP_ALIGN.CENTER)
rect(s, 2.99, 3.43, 1.65, 1.1, PALE)
text(s, 3.1, 3.65, 1.43, .7, "Entrada\ncomún", 20, PURPLE, True, PP_ALIGN.CENTER)
for y, zone in [(2.65, "A"), (4.38, "B")]:
    rect(s, 5.43, y, 3.2, 1.33, WHITE, LINE)
    text(s, 5.62, y + .14, 2.8, .32, f"ZONA {zone} · SERVIDOR PRIVADO", 12, PURPLE, True)
    text(s, 5.62, y + .59, 2.8, .52, f"Copia {zone} de la tienda", 20, INK, True)
rect(s, 9.41, 2.8, 2.75, 2.66, PALE)
text(s, 9.62, 3.03, 2.3, .69, "Datos\ncompartidos", 22, PURPLE, True)
text(s, 9.62, 4.15, 2.3, .9, "Productos\nCarritos · Pedidos", 17.5)
line(s, 2.17, 3.97, 2.84, 3.97, PURPLE, 1.6, True)
line(s, 4.65, 3.98, 5.03, 3.98, PURPLE, 1.6)
line(s, 5.03, 3.30, 5.03, 5.05, PURPLE, 1.6)
line(s, 5.03, 3.30, 5.30, 3.30, PURPLE, 1.6, True)
line(s, 5.03, 5.05, 5.30, 5.05, PURPLE, 1.6, True)
line(s, 8.65, 3.32, 9.26, 3.32, PURPLE, 1.6, True)
line(s, 8.65, 5.04, 9.26, 5.04, PURPLE, 1.6, True)
takeaway(s, "Dos copias de la tienda usan los mismos servicios de datos.", size=19.5)
note(s, "arquitectura", "Una tienda, dos copias y datos compartidos", 60, "Juan Pablo",
     "Este es el mapa suficiente para entender la solución. El usuario llega a un balanceador público de AWS, el ALB. "
     "El balanceador distribuye las solicitudes entre dos EC2 privadas, una en cada zona. Dentro de cada máquina corre "
     "un kind con una copia completa de los cinco servicios. Los datos administrados son compartidos por ambas copias: "
     "MySQL para Catalog, PostgreSQL para Orders, Redis para Checkout, DynamoDB para Cart y SQS para eventos de Orders. "
     "Terraform administra la red, el cómputo, los datos y los objetos Kubernetes. "
     "Los kind son independientes: no se trasladan pods de una EC2 a la otra. Aumentar réplicas de UI no aumenta la CPU "
     "ni la memoria física. La separación de zonas permite tener dos copias detrás del ALB, pero no debe presentarse como "
     "una demostración completa de alta disponibilidad de producción. Los puertos, CIDR, acceso SSM y políticas de red "
     "están en los anexos para responder preguntas.",
     transition="Con esta base, podemos mostrar cuatro decisiones operativas concretas.",
     sources=("Preentrega vigente · secciones 2–4", "README · implementación EC2 + kind"))

# Casos operativos: solo guion y notas; no generan láminas individuales.
DEMO_CASES = [{'key': 'drift',
  'title': 'Un cambio manual también debe ser visible',
  'seconds': 150,
  'speaker': 'Federico',
  'script': 'Cambiar solo la etiqueta Name de la VPC del proyecto desde la consola AWS, de the-store a '
            'the-store-demo. Revisar que plan proponga restaurar ese nombre sin otras acciones inesperadas. '
            'Aplicar, comprobar el nombre original y repetir plan. Terraform detecta diferencias al '
            'planificar; no vigila continuamente el entorno.',
  'demo': 'Identificar por ID la VPC del proyecto antes de exponer. Desde la consola cambiar únicamente Name. '
          'Desde la raíz del repo: terraform -chdir=terraform plan; terraform -chdir=terraform apply, '
          'revisando su nuevo plan antes de confirmar; volver a ejecutar plan. El proyecto usa una sola '
          'configuración. No proyectar estados completos ni datos sensibles.',
  'sources': ('Preentrega vigente · caso 1', 'terraform/modules/red/main.tf', 'README.md · casos de uso')},
 {'key': 'replicas',
  'title': 'Más réplicas de UI, con un cambio revisable',
  'seconds': 135,
  'speaker': 'Federico',
  'script': 'Cambiar replicas.ui de 2 a 4 en terraform/terraform.tfvars, manteniendo los otros servicios en 2. '
            'Revisar plan y aplicar. Comprobar cuatro réplicas disponibles de UI en ambos kind y la respuesta '
            'de la tienda. El total previsto de pods app cambia de 20 a 24; siguen existiendo dos EC2. Volver '
            'a ui=2 y comprobar el baseline. La prueba no aumenta CPU ni memoria de los hosts ni mide '
            'rendimiento.',
  'demo': 'Ejecutar terraform -chdir=terraform plan y terraform -chdir=terraform apply. Inspeccionar A y B con '
          'kubectl --kubeconfig .local/kind-a.kubeconfig get deployment,pods -n the-store y el comando '
          'equivalente para kind-b. Esperar réplicas disponibles, no solo deseadas. Restaurar ui=2, '
          'revisar/aplicar y comprobar.',
  'sources': ('Preentrega vigente · caso 2',
              'terraform/terraform.tfvars',
              'terraform/modules/aplicacion/main.tf')},
 {'key': 'versiones',
  'title': 'Publicar una versión y poder volver',
  'seconds': 165,
  'speaker': 'Federico',
  'script': 'Seleccionar app_version v1, luego v2 y volver a v1. Las dos versiones deben haberse publicado '
            'durante la preparación inicial en ECR con tags inmutables. Cambiar solo la selección actualiza '
            'las imágenes de los Deployments; comprobar en plan que no se reconstruyan imágenes durante el '
            'caso. Mostrar The Store · v1/v2 en el encabezado, el rollout de ambas copias y la respuesta de la '
            'tienda. El frontend original conserva su diseño: se agregó esa identificación de versión para la '
            'demo. Volver a una imagen anterior no revierte datos ni migraciones y no garantiza por sí solo '
            'ausencia de interrupciones.',
  'demo': 'Editar app_version en terraform/terraform.tfvars, revisar plan y aplicar desde terraform/. '
          'Comprobar A/B con sus kubeconfigs y abrir /catalog. Usar v1→v2→v1; verificar las imágenes esperadas '
          'al regresar. Para afirmar continuidad hace falta una medición real ensayada, no solo una respuesta '
          'final de UI.',
  'sources': ('Preentrega vigente · caso 3',
              'terraform/modules/imagenes/main.tf',
              'the-store/src/ui/Dockerfile',
              'README.md · casos de uso')},
 {'key': 'cuarentena',
  'title': 'Aislar Checkout y conservar catálogo y carrito',
  'seconds': 180,
  'speaker': 'Federico',
  'script': 'Simular la decisión de aislar Checkout agregándolo a quarantine. El plan debe limitar el cambio a '
            'NetworkPolicies en ambos kind. Comprobar catálogo y carrito funcionales y compra bloqueada, con '
            'sondas válidas. Vaciar quarantine, revisar y aplicar, y comprobar una compra real. No se simula '
            'un ataque real. Si se afirma que no hubo reinicios, comparar UID y restartCount antes/después. No '
            'aceptar cualquier timeout como evidencia de aislamiento.',
  'demo': 'Editar quarantine=[] → ["checkout"] → [] en terraform/terraform.tfvars; plan y apply en cada '
          'transición. Mostrar el efecto por navegador y revisar ambas copias. Mantener una sola persona '
          'operando. Restaurar el baseline y comprobar compra antes de cerrar.',
  'sources': ('Preentrega vigente · caso 4',
              'terraform/modules/aplicacion/politicas.tf',
              'README.md · casos de uso')}]

# Opcional: texto solicitado, sin inventar usos de IA.
s = base("Opcional", "", "", hidden=True)
text(s, .8, 2.82, 11.7, 1.0, "Slide de uso de IA", 44, PURPLE, True)
note(s, "ia", "Slide de uso de IA", 0, "A definir", "Lámina opcional y oculta por pedido del usuario. "
     "Conserva únicamente el texto marcador. Completar con usos reales y validación del grupo antes de habilitarla. "
     "Si se incorpora, usar hasta 30 segundos del margen de transición.", hidden=True)

# 13 — Único separador para pasar a compartir pantalla.
s = base("En vivo", "", "13", PALE)
text(s, .8, 1.67, 10.9, 1.2, "Demo.", 76, PURPLE, True)
text(s, .85, 3.3, 11.1, 1.0, "De la configuración\na la tienda funcionando.", 35, INK, True)
line(s, .85, 5.33, 4.4, 5.33, PURPLE, 1.4)
text(s, .85, 5.69, 10.9, .55, "Terraform sobre nuestra infraestructura en AWS", 23, MUTED)
note(s, "demo", "Demo en vivo", 660, "Federico",
     "Cambiar a la tienda y la terminal. Los cuatro casos se realizan compartiendo pantalla y no tienen láminas "
     "individuales. Entorno creado con antelación; una sola persona opera. Mostrar la acción, el plan y el efecto "
     "de cada caso, restaurando el baseline antes de continuar. Abrir catálogo y confirmar compra de prueba si el "
     "ensayo permite incluirla. El tiempo total de 11 minutos incluye presentación de entorno y los cuatro casos.",
     demo="\n\n".join(c['title'] + "\n" + c['script'] + "\n\nOPERADOR\n" + c['demo'] for c in DEMO_CASES),
     transition="Después de la demostración, volver a la lámina de cierre.",
     sources=("Preentrega vigente · sección 3",))

# 14 — Cierre orientado a la decisión.
s = base("Cierre", "Una forma más controlada de operar The Store", "14")
claims = [("Entregar", "Automatizar y estandarizar la creación de entornos."),
          ("Controlar", "Versionar cambios y revisar configuración y seguridad."),
          ("Reutilizar", "Adaptar el modelo y retirar lo que dejamos de usar.")]
for i, (a, b) in enumerate(claims):
    y = 2.65 + i * 1.0
    text(s, .8, y, 2.47, .58, a, 30, PURPLE, True)
    text(s, 3.6, y + .07, 8.65, .62, b, 23)
    line(s, .8, y + .78, 12.5, y + .78)
takeaway(s, "Adoptar Terraform para reducir tareas manuales y hacer cambios controlados.", size=20)
note(s, "cierre", "Una forma más controlada de operar The Store", 45, "Matias",
     "Cerrar con la propuesta de adopción de Terraform. Para entregar: automatización y consistencia. Para controlar: "
     "versiones, seguridad revisable y documentación del estado esperado. Para reutilizar: módulos y recursos temporales "
     "que podemos retirar cuando dejan de ser necesarios. La herramienta concreta aporta providers, lenguaje declarativo, "
     "plan, estado y resolución de dependencias. La demostración conecta esas capacidades con The Store. "
     "La decisión propuesta es incorporar Terraform al proceso del equipo, con revisión y pruebas. El POC usa AWS "
     "Academy y dos kind independientes; la adopción productiva requiere resolver los límites de capacidad, TLS y "
     "operación que figuran en el respaldo. No atribuir porcentajes de ahorro o resultados que no se hayan medido.",
     transition="Abrimos las preguntas.")

# 15 — Preguntas y enlace real.
s = base("Grupo 2", "", "15")
text(s, .8, 2.0, 11.6, 1.1, "Preguntas.", 64, PURPLE, True)
text(s, .85, 3.55, 11.2, .65, "Proyecto y guía de uso", 25, INK, True)
link = text(s, .85, 4.35, 11.2, .5, "github.com/mrossisei/the-store-iac", 24, PURPLE)
link_run = link.text_frame.paragraphs[0].runs[0]
link_run.hyperlink.address = "https://github.com/mrossisei/the-store-iac"
link_run.font.color.rgb = rgb(PURPLE)
link_run.font.underline = False
text(s, .85, 5.68, 11.2, .44, "Matias Rossi · Juan Pablo Birsa · Federico Viera", 20, MUTED)
annex_link = text(s, .85, 6.26, 4.5, .3, "Consultar anexos técnicos →", 15, PURPLE)
questions_slide = s
note(s, "preguntas", "Preguntas", 0, "Todos",
     "Reservar cinco minutos finales. Los tres integrantes deben poder explicar la solución completa. "
     "La navegación a los anexos está vinculada desde esta lámina. Abrir solo el respaldo relacionado con la consulta. "
     "El PPT contiene notas del orador y una lámina opcional de IA oculta.",
     sources=("https://github.com/mrossisei/the-store-iac",))


def annex(title, code):
    s = base("Anexo · respaldo para preguntas", title, code, hidden=True)
    back = text(s, 9.55, 6.46, 3.0, .25, "Volver a preguntas →", 12, PURPLE, align=PP_ALIGN.RIGHT)
    back.click_action.target_slide = questions_slide
    return s


# A1 — Alcance y límites como respaldo, sin estados internos de tareas en el PPT.
s = annex("Qué cubre el POC y qué requiere otro trabajo", "A1")
annex_link.click_action.target_slide = s
text(s, .8, 2.4, 5.4, .45, "Dentro del alcance", 25, PURPLE, True)
text(s, .8, 3.12, 5.4, 2.5,
     "Red AWS y dos EC2 privadas con kind.\nALB, imágenes y datos compartidos.\nDespliegues y políticas con Terraform.\nCuatro casos de operación.", 21)
text(s, 7.0, 2.4, 5.4, .45, "Límites", 25, INK, True)
text(s, 7.0, 3.12, 5.4, 2.8,
     "Dos clústeres independientes.\nRéplicas limitadas por cada EC2.\nSin HTTPS público, CI/CD ni observabilidad.\nSin autoescalado ni EKS.", 21)
note(s, "alcance", "Qué cubre el POC y qué requiere otro trabajo", 0, "Todos",
     'El POC usa dos EC2 privadas, cada una con kind independiente, ALB, datos compartidos, imágenes y aplicación administrados desde terraform/. EKS, HTTPS público, CI/CD, observabilidad, autoescalado y roles separados por servicio quedan fuera del alcance. Se reutilizan LabRole y LabInstanceProfile. Las réplicas internas no reprograman pods entre EC2. Consultar README y la preentrega vigente para los límites y la preparación.', hidden=True,
     sources=("Preentrega vigente · secciones 2–3", "README · alcance"))

# A2 — Red y camino HTTP, con tipografía de respaldo legible.
s = annex("Red y recorrido de una solicitud", "A2")
text(s, .8, 2.33, 11.5, .8, "Cliente → ALB :80 → EC2 :8080 → kind :30080 → UI :8080", 23, PURPLE, True)
network_rows = [("VPC", "10.0.0.0/16"),
                ("Públicas · A / B", "10.0.1.0/24  /  10.0.2.0/24"),
                ("Privadas · A / B", "10.0.16.0/24  /  10.0.32.0/24"),
                ("Datos · A / B", "10.0.48.0/24  /  10.0.49.0/24"),
                ("Internas de cada kind", "Pods: 10.244.0.0/16  ·  Services: 172.20.0.0/16")]
for i, (a, b) in enumerate(network_rows):
    y = 3.26 + .55 * i
    text(s, .8, y, 3.8, .35, a, 17, INK, True)
    text(s, 4.7, y, 7.8, .39, b, 17, MUTED)
    line(s, .8, y + .43, 12.5, y + .43)
note(s, "red", "Red y recorrido de una solicitud", 0, "Juan Pablo",
     "Cada AZ tiene subred pública, privada y de datos. ALB y NAT están en las públicas. Cada privada tiene una EC2 "
     "sin IP pública y la interfaz del endpoint SQS. Las subredes de datos alojan RDS/Redis y no tienen ruta por defecto "
     "a Internet. Las privadas salen por el NAT de su propia zona. Hay endpoints Gateway para S3/DynamoDB e Interface "
     "para SQS. El ALB acepta HTTP/80 y solo él puede alcanzar EC2:8080 según SG. kind mapea host8080 a NodePort30080 "
     "y la UI escucha8080. SG de datos permite MySQL3306, PostgreSQL5432 y Redis6379 solo desde EC2. "
     "Los CIDR de pods y Services son internos de cada kind, no subredes AWS y no deben interpretarse como red compartida "
     "entre las EC2. Administración autenticada con SSM y TLS hacia las dos APIs, usando los puertos locales16443 y26443.",
     hidden=True, sources=("Preentrega vigente · sección 4", "terraform/terraform.tfvars", "README y configuración Terraform"))

# A3 — Configuración y estado de la implementación actual.
s = annex("Una configuración y un estado compartido", "A3")
for i, (heading, body) in enumerate([
    ("Configuración", "Una raíz Terraform con cinco módulos propios"),
    ("Estado en S3", "Registro compartido de los recursos gestionados"),
    ("Operación", "Plan, apply y destroy desde la misma configuración")]):
    y = 2.48 + i * .91
    text(s, .8, y, 3.1, .52, heading, 24, PURPLE, True)
    text(s, 4.25, y + .02, 8.2, .52, body, 23)
    line(s, .8, y + .70, 12.5, y + .70)
text(s, .8, 5.57, 11.7, .55, "S3 cifrado + versionado + bloqueo. Bucket preparado antes de init.", 20, INK, True)
note(s, "estado", "Una configuración y un estado compartido", 0, "Juan Pablo",
     "La versión simplificada actual opera desde terraform/ con un estado S3: the-store/kind/terraform.tfstate. "
     "main.tf conecta red, imágenes, cómputo, datos y dos instancias del módulo de aplicación. "
     "El bucket debe existir antes de init y su preparación está en README. El backend habilita encrypt y "
     "use_lockfile; el bucket se configura con versionado. Terraform invoca scripts/acceso-kind.sh para esperar "
     "los clústeres y abrir túneles SSM a sus API. El retiro se solicita desde la misma raíz con destroy, "
     "revisando las dependencias y el plan. Auditar recursos después; el bucket del estado y los roles "
     "preexistentes se conservan fuera de esa destrucción. Retirar datos administrados puede eliminarlos; "
     "el estado versionado no reemplaza sus backups. No proyectar estados o kubeconfigs completos.",
     hidden=True, sources=("README.md · cómo levantar y destruir", "terraform/providers.tf", "terraform/main.tf"))

# A4 — Alternativas sin afirmaciones históricas heredadas incorrectas.
s = annex("Por qué elegimos esta combinación", "A4")
alternatives = [("Terraform / Pulumi", "HCL declarativo, experiencia del grupo y ecosistema AWS."),
                ("ALB / NLB + nginx", "La app usa HTTP; ALB evita sumar otro proxy en este POC."),
                ("kind / EKS", "kind en EC2 es el alcance aprobado; EKS queda como ampliación.")]
for i, (a, b) in enumerate(alternatives):
    y = 2.56 + i * 1.1
    text(s, .8, y, 4.07, .62, a, 24, PURPLE, True)
    text(s, 5.14, y, 7.3, .76, b, 22)
    line(s, .8, y + .88, 12.5, y + .88)
note(s, "alternativas", "Por qué elegimos esta combinación", 0, "Todos",
     "La preentrega compara Pulumi con Terraform: el grupo eligió HCL, ya conocía Terraform y valoró el ecosistema. "
     "Eso no implica que Pulumi no pueda gestionar la arquitectura. También compara NLB más nginx con ALB: "
     "para el tráfico HTTP de esta tienda el ALB evita agregar un proxy que deba mantenerse. "
     "kind en EC2 es el alcance aprobado vigente, con un clúster independiente por host. No heredar las decisiones "
     "de los documentos antiguos sobre EKS/NLB. Las limitaciones del Lab condicionan tamaños y permisos. "
     "No decir que kind no es Kubernetes real: usa su API y nodos en contenedores. El costo no está actualizado ni "
     "medido para la presentación, por eso no se muestra el importe del diseño histórico.",
     hidden=True, sources=("Preentrega vigente · secciones 2, 3 y 5",))

# A5 — Operaciones especiales: respaldo técnico.
s = annex("Gestionar también lo que ya está creado", "A5")
special = [("Detectar drift", "El plan consulta y compara los recursos administrados."),
           ("Importar", "Incorporar recursos existentes a la gestión con Terraform."),
           ("Reemplazar", "Planificar la recreación explícita de un recurso."),
           ("Retirar", "Revisar el alcance antes de eliminar un entorno.")]
for i, (a, b) in enumerate(special):
    y = 2.46 + i * .83
    text(s, .8, y, 3.1, .45, a, 23, PURPLE, True)
    text(s, 4.25, y, 8.2, .60, b, 21)
    line(s, .8, y + .64, 12.5, y + .64)
note(s, "especiales", "Gestionar también lo que ya está creado", 0, "Juan Pablo",
     "Terraform permite operar sobre recursos existentes. El plan detecta diferencias "
     "de los atributos que el provider consulta y administra; no es un monitor continuo de cualquier cambio. "
     "Import o un bloque import vincula un recurso ya existente al estado; debe acompañarse de configuración "
     "apropiada y revisión. No demostramos importación en los cuatro casos. plan -replace=ADDRESS solicita "
     "planificar la sustitución de un recurso y puede afectar el servicio; tampoco se ejecuta en la demo. "
     "plan -destroy deja ver el alcance de una eliminación sin realizarla. No usar -target como forma rutinaria "
     "de aplicar una parte aislada del proyecto. El rollback mostrado selecciona imágenes anteriores; no es una "
     "restauración universal de infraestructura ni de datos.", hidden=True,
     sources=("https://developer.hashicorp.com/terraform/cli/commands/import", "https://developer.hashicorp.com/terraform/cli/commands/plan", "https://developer.hashicorp.com/terraform/cli/commands/destroy"))

# A6 — Atribución precisa y trazabilidad, sin enlazar recursos privados.
s = annex("Fuentes y documentación de respaldo", "A6")
refs = [("Material de clase", "82.08 Cloud Computing · IaC / Terraform · 33 páginas"),
        ("Alcance y equipo", "Pre Entrega - Grupo 2 -1.pdf · versión vigente"),
        ("Implementación", "README · terraform/ · scripts/acceso-kind.sh"),
        ("Terraform", "developer.hashicorp.com/terraform/intro"),
        ("Capacidades y CLI", "developer.hashicorp.com/terraform · documentación oficial"),
        ("Repositorio", "github.com/mrossisei/the-store-iac")]
for i, (a, b) in enumerate(refs):
    y = 2.45 + i * .66
    text(s, .8, y, 3.1, .4, a, 19, PURPLE, True)
    text(s, 4.35, y, 8.1, .48, b, 18, INK)
    line(s, .8, y + .48, 12.5, y + .48)
note(s, "fuentes", "Fuentes y documentación de respaldo", 0, "Todos",
     'La clase adjunta 10-IaC_Terraform.pptx (1).pdf, de 82.08 Cloud Computing, aporta ventajas y capacidades generales. La preentrega vigente de Redes de Información es la autoridad de integrantes, legajos y alcance. Se contrastó el respaldo operativo con la versión simplificada actual en main: una configuración terraform/, un backend S3 y scripts/acceso-kind.sh. Los ejemplos empresariales ilustran adopción y no son nuevos ambientes implementados. No se ejecutaron operaciones AWS ni demos al generar esta presentación.',
     hidden=True, sources=("https://developer.hashicorp.com/terraform/intro", "https://developer.hashicorp.com/terraform/cli/commands/plan", "https://developer.hashicorp.com/terraform/cli/commands/apply", "https://developer.hashicorp.com/terraform/cli/state", "https://developer.hashicorp.com/terraform/language/modules", "https://developer.hashicorp.com/terraform/language/state/purpose", "https://developer.hashicorp.com/terraform/internals/graph", "https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle", "https://developer.hashicorp.com/terraform/language/backend/s3", "https://developer.hashicorp.com/terraform/cli/commands/import", "https://developer.hashicorp.com/terraform/cli/commands/destroy", "https://github.com/mrossisei/the-store-iac"))

# Anular efectos heredados del tema: composición plana sin sombras en formas o líneas.
for slide in prs.slides:
    for shape in slide.shapes:
        for ref in shape._element.xpath("./p:style/a:effectRef"):
            ref.set("idx", "0")
        sppr = getattr(shape._element, "spPr", None)
        if sppr is not None:
            for effect in list(sppr):
                if effect.tag in ("{http://schemas.openxmlformats.org/drawingml/2006/main}effectLst",
                                  "{http://schemas.openxmlformats.org/drawingml/2006/main}effectDag"):
                    sppr.remove(effect)
            sppr.append(OxmlElement("a:effectLst"))

# Comprobación geométrica: todos los textos deben permanecer dentro del lienzo.
for page, x, y, w, h, value in BOUNDS:
    assert x >= 0 and y >= 0 and x + w <= 13.334 and y + h <= 7.501, (page, value)

prs.save(OUT / "presentacion.pptx")
(OUT / "estructura.json").write_text(json.dumps(SLIDES, ensure_ascii=False, indent=2) + "\n")

main_count = sum(not e["hidden"] for e in SLIDES)

md = ["# Presentación — The Store con Terraform", "",
      "PPT editorial clara, 16:9. Grupo 2 · 72.20 Redes de Información · ITBA · 2C 2026.", "",
      "- Matias Rossi — 63202", "- Juan Pablo Birsa — 64500", "- Federico Viera — 62022", "",
      "## Archivos y uso", "",
      "- `presentacion.pptx`: texto y diagramas editables, con notas del orador.",
      f"- `presentacion.pdf`: las {main_count} láminas del recorrido principal.",
      "- `anexos.pdf`: seis láminas técnicas de respaldo, separadas del recorrido.",
      "- `guion-presentacion.md`: este guion y la preparación de la demo.",
      "- `estructura.json`: contenido de notas, tiempos e índices para regeneración.", "",
      "La lámina **Slide de uso de IA** está oculta antes de la demo. Los anexos también están ocultos; "
      "se accede a ellos desde el vínculo de la lámina Preguntas. Para usar IA, completar solo con usos reales "
      "del grupo y habilitar esa lámina desde PowerPoint/Impress. El PDF principal no incluye las láminas ocultas.", "",
      "## Tiempo y reparto propuesto", "",
      "Contenido: **24 min**. Reservar **1 min** para transiciones y **5 min** para preguntas. "
      "Si se habilita IA, usar hasta 30 s del margen. El tiempo de demo es una estimación a medir en ensayo; "
      "no presupone que las operaciones AWS ya fueron cronometradas.", "",
      "- Matias: contexto y propuesta; vuelve al cierre.",
      "- Juan Pablo: Terraform, beneficios, ejemplos de adopción y arquitectura.",
      "- Federico: demo. Una sola persona opera la sesión.", "",
      "El reparto es una propuesta editable. Los tres deben poder explicar la implementación completa.", "",
      "## Guion por diapositiva", ""]
visible_number = 0
for entry in SLIDES:
    if entry["hidden"]:
        heading = "Opcional" if entry["key"] == "ia" else "Anexo"
    else:
        visible_number += 1
        heading = str(visible_number)
    status = " · oculta/opcional" if entry["hidden"] else ""
    md += [f'### {heading}. {entry["title"]}{status}', "",
           f'**Orador:** {entry["speaker"]}. **Tiempo objetivo:** {entry["seconds"]} s.', "", entry["script"], ""]
    if entry["demo"]:
        md += ["**Operador / demo:**", "", "Ver la sección Cuatro casos para compartir pantalla." if entry["key"] == "demo" else entry["demo"], ""]
    if entry["transition"]:
        md += ["**Transición:** " + entry["transition"], ""]
    if entry["technical_support"]:
        md += ["<details><summary>Respaldo para preguntas — no leer como guion</summary>", "", entry["technical_support"], "", "</details>", ""]
    if entry["sources"]:
        md += ["**Fuentes:**", ""] + ["- " + x for x in entry["sources"]] + [""]

md += ["## Cuatro casos para compartir pantalla — sin diapositivas", ""]
for case in DEMO_CASES:
    md += ["### " + case["title"], "", case["script"], "", "**Operador:**", "", case["demo"], ""]

DEMO_GUIDE = '## Preparación de la demo\n\nLa implementación vigente usa **una sola raíz `terraform/` y un estado remoto S3**. Los comandos de este guion se ejecutan desde la raíz del repositorio. El detalle de preparación está en README.md. Esta generación solo produce documentos: no certifica pruebas nuevas ni ejecuta AWS.\n\n### Antes de exponer\n\n1. Preparar el bucket y el backend siguiendo README; no crear un bucket adicional para ocultar errores de permisos.\n2. Tener credenciales vigentes, presupuesto y tiempo de sesión suficientes en AWS Academy.\n3. Crear el entorno con antelación. Terraform construye/publica v1/v2 en la preparación inicial y crea los recursos; no esperar esa creación durante la exposición.\n4. Confirmar UI=2 por kind, versión v1 y quarantine=[]. Comprobar las dos copias, los dos targets del ALB y una compra real.\n5. Preparar el navegador en la tienda, la consola en la VPC propia y el editor en terraform/terraform.tfvars.\n6. Ensayar los cuatro casos y guardar capturas o video reales, asociados a versión/commit. No usar diagramas como evidencia.\n7. Verificar pantalla compartida y VPN; una sola persona opera el entorno. No mostrar claves, contraseñas, estados completos o kubeconfigs.\n\n### Preparación y operación\n\nCon el backend inicializado según README:\n\n```bash\nterraform -chdir=terraform plan\nterraform -chdir=terraform apply\nterraform -chdir=terraform output url\n```\n\nEn plan/apply, Terraform invoca scripts/acceso-kind.sh para comprobar los kind y abrir los túneles. El primer despliegue puede tardar varios minutos. Durante los casos, revisar el plan completo para detectar altas, bajas o reemplazos inesperados. Si se ejecuta apply sin un plan guardado, se calcula un nuevo plan y se revisa antes de confirmar.\n\n### Inspección de ambas copias\n\nLos kubeconfigs privados quedan bajo .local/. Sin mostrar su contenido:\n\n```bash\nkubectl --kubeconfig .local/kind-a.kubeconfig get deployment,pods -n the-store\nkubectl --kubeconfig .local/kind-b.kubeconfig get deployment,pods -n the-store\n```\n\nIdentificar A y B explícitamente. Si el acceso falla, diagnosticar el túnel antes de interpretar resultados de la aplicación. No imprimir Secrets ni planes/estados completos frente al público.\n\n### Lista de comprobación por caso\n\n| Caso | Cambio | Lo que se debe observar | Vuelta al inicio |\n|---|---|---|---|\n| Drift | Name de la VPC desde consola | Plan propone restaurar solo esa etiqueta | Name original y plan sin cambios |\n| Réplicas | UI 2→4 por kind | UI disponible 4/4 en ambos; 24 pods app; 2 EC2 | UI 2; 20 pods app |\n| Versión | app_version v1→v2 | Etiqueta visible, rollout e imágenes en ambas copias | v1 e imágenes esperadas |\n| Cuarentena | checkout en quarantine | Cambian policies; catálogo/carrito sanos; compra bloqueada | Lista vacía y compra real |\n\nTodos los parámetros están en terraform/terraform.tfvars. Los números describen el caso previsto, no pruebas ejecutadas al generar el PPT. Cambiar app_version selecciona una versión ya publicada: confirmar en plan que no haya reconstrucciones inesperadas. La etiqueta de versión del frontend se agregó para observar ese caso; no es un rediseño de la tienda.\n\n### Si se supera el tiempo ensayado\n\nPasar a una grabación real del mismo caso e identificarla como respaldo. Si falta evidencia, no atribuir un resultado. Restaurar el baseline antes de seguir y reservar margen para el cierre.\n\n### Al terminar\n\nRevisar el alcance y ejecutar el procedimiento actual:\n\n```bash\nterraform -chdir=terraform plan -destroy\nterraform -chdir=terraform destroy\n```\n\nDespués auditar recursos por IDs/tags. El bucket remoto y los roles preexistentes permanecen. El destroy de esta configuración incluye los recursos que administra; no asumir que conserva ECR, bases o datos. No iniciar la destrucción durante la demo.\n\n## Regeneración\n\n```bash\npython3 -m venv /tmp/ppt-terraform-venv\n/tmp/ppt-terraform-venv/bin/pip install python-pptx==1.0.2\n/tmp/ppt-terraform-venv/bin/python scripts/generar-presentacion.py\n```\n\nExportar el PPT a PDF sin las láminas ocultas para el recorrido principal. Exportar los anexos aparte. Los textos y diagramas siguen siendo editables. La correspondencia con la clase se documenta en docs/referencia-clase-terraform.md.\n'
md += DEMO_GUIDE.splitlines()

(OUT / "guion-presentacion.md").write_text("\n".join(md))
print(json.dumps({"pptx": str(OUT / "presentacion.pptx"), "slides": len(SLIDES),
                  "main": sum(not e["hidden"] for e in SLIDES),
                  "hidden": sum(e["hidden"] for e in SLIDES),
                  "seconds": sum(e["seconds"] for e in SLIDES)}, ensure_ascii=False))
