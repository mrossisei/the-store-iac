#!/usr/bin/env python3
"""Genera la presentación T14 editable. Requiere python-pptx."""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT = Path(__file__).resolve().parents[1]
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLUE, DARK, GRAY, PALE = '326CE5', '1A2332', '4A5568', 'EDF3FF'

def box(slide, x, y, w, h, fill, line=None):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = RGBColor.from_string(fill)
    sh.line.fill.background() if line is None else None
    if line: sh.line.color.rgb = RGBColor.from_string(line)
    return sh

def text(slide, x, y, w, h, value, size=22, color=DARK, bold=False, align=PP_ALIGN.LEFT):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame; tf.clear(); tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(.05); tf.margin_top = tf.margin_bottom = Inches(.03)
    p = tf.paragraphs[0]; p.text = value; p.alignment = align
    p.font.name = 'Calibri'; p.font.size = Pt(size); p.font.bold = bold; p.font.color.rgb = RGBColor.from_string(color)
    return shape

def base(section, title):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box(slide, 0, 0, 13.333, .09, BLUE)
    text(slide, .65, .25, 11.8, .35, section.upper(), 13, BLUE, True)
    text(slide, .65, .7, 12, .62, title, 32, DARK, True)
    box(slide, .65, 1.45, 12, .025, BLUE)
    text(slide, .65, 7.12, 10, .22, 'THE STORE  |  INFRAESTRUCTURA COMO CÓDIGO', 10, GRAY)
    text(slide, 12.1, 7.08, .5, .25, str(len(prs.slides)), 11, GRAY, align=PP_ALIGN.RIGHT)
    return slide

def bullets(section, title, items, note=None):
    s = base(section, title)
    y = 1.85
    for item in items:
        box(s, .78, y+.14, .09, .09, BLUE)
        text(s, 1.05, y, 11.35, .8, item, 23)
        y += .95
    if note: text(s, .8, 6.53, 11.7, .45, note, 16, GRAY)
    return s

def card(s, x, y, w, h, heading, body):
    box(s, x, y, w, h, PALE)
    text(s, x+.15, y+.12, w-.3, .42, heading, 21, BLUE, True, PP_ALIGN.CENTER)
    text(s, x+.15, y+.68, w-.3, h-.75, body, 20, DARK, False, PP_ALIGN.CENTER)

s = prs.slides.add_slide(prs.slide_layouts[6]); box(s, 0, 0, .25, 7.5, BLUE)
text(s, .95, 1.1, 11, .5, 'TRABAJO PRÁCTICO  |  REDES', 18, BLUE, True)
text(s, .95, 1.85, 11.4, 1.5, 'The Store en AWS\ncon Terraform y Kubernetes', 38, DARK, True)
text(s, .98, 4.25, 10.7, .5, 'Infraestructura reproducible · dos copias independientes', 24, GRAY)
text(s, .98, 5.55, 10.5, .5, 'Matías  ·  Juan Pablo  ·  Federico', 24, DARK)
text(s, .98, 6.8, 11, .3, 'T14  |  Borrador para cierre y ensayo', 15, GRAY)

bullets('Contexto', 'El problema: repetir sin improvisar', [
    'La infraestructura manual es difícil de repetir y auditar.',
    'Terraform describe recursos, muestra cambios y conserva estado.',
    'The Store reúne UI, catálogo, carrito, checkout y órdenes.',
    'Dos copias sirven la misma tienda con datos compartidos.'])
bullets('Objetivo', 'Cuatro casos para demostrar control', [
    'Detectar y corregir drift en un recurso AWS.',
    'Escalar réplicas de UI y volver al valor inicial.',
    'Cambiar de versión y verificar el rollback.',
    'Aislar Checkout y restaurar el flujo de compra.'])
s = base('Arquitectura', 'Dos zonas, dos copias, datos compartidos')
card(s, .85, 2.0, 2.2, 1.35, 'Navegador', 'HTTP :80')
card(s, 3.65, 2.0, 2.2, 1.35, 'ALB público', 'targets :8080')
card(s, 6.5, 1.75, 2.5, 1.55, 'AZ A', 'EC2 privada\nkind A')
card(s, 6.5, 3.6, 2.5, 1.55, 'AZ B', 'EC2 privada\nkind B')
card(s, 9.8, 2.35, 2.65, 2.3, 'Datos AWS', 'RDS · Redis\nDynamoDB · SQS')
text(s, 3.05, 2.36, .6, .4, '→', 28, BLUE, True); text(s, 5.85, 2.36, .6, .4, '→', 28, BLUE, True)
text(s, 5.85, 4.02, .6, .4, '→', 28, BLUE, True)
text(s, 9.05, 2.36, .7, .4, '→', 28, BLUE, True); text(s, 9.05, 4.02, .7, .4, '→', 28, BLUE, True)
text(s, 1, 5.85, 11.4, .65, 'VPC 10.0.0.0/16 · seis subredes /24 · una EC2 por AZ', 21, GRAY, align=PP_ALIGN.CENTER)
s = base('Kubernetes', 'Cada EC2 aloja un kind independiente')
card(s, 1, 2, 5.25, 2.9, 'EC2 A  /  kind A', 'Control plane + worker\n5 servicios · 10 pods base\nCalico y policies propias')
card(s, 7.05, 2, 5.25, 2.9, 'EC2 B  /  kind B', 'Control plane + worker\n5 servicios · 10 pods base\nCalico y policies propias')
text(s, 1, 5.5, 11.3, .85, 'No comparten nodos ni reprograman pods entre EC2. Escalar UI no agrega capacidad física.', 22, DARK, align=PP_ALIGN.CENTER)
bullets('Recorrido', 'De la solicitud a la compra', [
    'Navegador → ALB :80 → EC2 :8080.',
    'Host → kind :30080 → NodePort UI → pod :8080.',
    'UI conecta con los servicios internos de cada copia.',
    'Ambas copias leen y escriben en datos AWS compartidos.'])
bullets('Seguridad', 'Capas de acceso y aislamiento', [
    'Security groups separan entrada pública, hosts y datos.',
    'Operador → SSM → API de cada kind con TLS.',
    'LabRole existente e IMDSv2 para acceso AWS.',
    'Calico NetworkPolicies controla tráfico entre pods.'])
bullets('Operación', 'Terraform: estados y orden', [
    'Bootstrap separado; estados S3 para infra, imágenes y aplicación.',
    'Plan revisado y bloqueo: un operador sobre el entorno compartido.',
    'Aplicar infraestructura antes de conectar y desplegar la app.',
    'Destruir aplicación con acceso activo; luego infraestructura.'])
bullets('Operación', 'Automatización: alcance pendiente', [
    'Plan, Apply y Destroy en GitHub Actions están planificados.',
    'T15 está en pausa: no se presenta como implementada ni probada.',
    'Una sola sesión AWS y un operador coordinan el entorno.',
    'El ciclo formal de recreación y auditoría corresponde a T13.'])
bullets('Validación', 'Evidencia disponible y pendiente', [
    'T00–T09: componentes y pruebas reales documentadas.',
    'T08: compra por API; T09: cuarentena y restauración.',
    'T11/T12: integración y campañas en prueba por el equipo.',
    'Faltan evidencia nueva, ensayo y cierre formal de T13/T14.'])
bullets('Demo 1', 'Drift: detectar y corregir', [
    'Partir de un recurso AWS y baseline conocidos.',
    'Introducir un cambio permitido fuera de Terraform.',
    'Mostrar el plan que detecta la diferencia y aplicar corrección.',
    'Verificar convergencia; registrar evidencia del caso.'], 'Campaña T12 pendiente de evidencia final.')
bullets('Demo 2', 'Réplicas: 2 → 4 → 2 por kind', [
    'Cambiar UI en la configuración de aplicación y revisar plan.',
    'Mostrar 20 → 24 → 20 pods de aplicación en total.',
    'Comprobar ambas copias y respuesta de la tienda.',
    'Siguen siendo dos EC2: no se agregan nodos físicos.'], 'Campaña T12 pendiente de evidencia final.')
bullets('Demo 3', 'Versiones: v1 → v2 → v1', [
    'Seleccionar imágenes existentes por digest en ECR.',
    'Revisar el plan y observar el rollout en ambos kind.',
    'Comprobar UI y hacer rollback a v1.',
    'La demo no construye ni publica imágenes.'], 'Campaña T12 pendiente de evidencia final.')
bullets('Demo 4', 'Cuarentena de Checkout', [
    'Activar aislamiento mediante NetworkPolicies y revisar el plan.',
    'Catálogo y carrito siguen; Checkout queda aislado.',
    'Comprobar UID estables y restaurar políticas.',
    'Verificar compra después de la restauración.'], 'T09 probó políticas; campaña integral T12 pendiente.')
bullets('Resultados', 'Lo probado y los límites del POC', [
    'T00–T09 documentan infraestructura, aplicación y políticas.',
    'Dos kind independientes comparten datos, no capacidad de cómputo.',
    'T11/T12 en prueba; falta evidencia nueva y ciclo formal T13.',
    'Disponibilidad y seguridad de producción requieren más trabajo.'])
s = base('Cierre', 'Repositorio y preguntas')
text(s, 1, 2.1, 11.3, .8, 'Código, contrato y guías de operación en el repositorio', 26, DARK, True)
text(s, 1, 3.2, 11.3, 1.3, 'docs/contrato-implementacion.md\ndocs/estado-tareas.md  ·  docs/presentacion.md', 23, BLUE)
text(s, 1, 5.15, 11, .7, 'Matías  ·  Juan Pablo  ·  Federico', 25, DARK)
text(s, 1, 6.1, 11, .5, 'Preguntas', 27, BLUE, True)

out = ROOT / 'docs/entrega/presentacion.pptx'; out.parent.mkdir(parents=True, exist_ok=True)
prs.save(out)
print(out)
