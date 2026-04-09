#!/usr/bin/env python3
"""
Plan Semanal de Comidas Saludables
Genera y envía por email un plan semanal de comidas usando la API de Claude.
Incluye PDF adjunto. Todas las recetas son preparables únicamente con microondas.
"""

import smtplib, os, io, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import anthropic
from xhtml2pdf import pisa

SENDER_EMAIL   = "laminarrieta@gmail.com"
RECEIVER_EMAIL = "laminarrieta@gmail.com"
SMTP_HOST      = "smtp.gmail.com"
SMTP_PORT      = 465

SEASONAL_PRODUCE = {
    1:  "naranjas, mandarinas, limones, kiwis, peras, manzanas, espinacas, acelgas, col, coliflor, brocoli, puerros, zanahorias, remolachas",
    2:  "naranjas, mandarinas, limones, kiwis, peras, manzanas, espinacas, acelgas, col, coliflor, brocoli, puerros, zanahorias",
    3:  "fresas, kiwis, naranjas, limones, espinacas, guisantes, esparragos, alcachofas, acelgas, zanahorias, puerros",
    4:  "fresas, kiwis, cerezas tempranas, esparragos, guisantes, alcachofas, espinacas, acelgas, lechuga, rabanos",
    5:  "fresas, cerezas, nisperos, esparragos, guisantes, habas, alcachofas, lechuga, rabanos, tomates tempranos",
    6:  "cerezas, melocotones, albaricoques, nectarinas, tomates, pepinos, pimientos, calabacines, berenjenas, judias verdes, lechuga",
    7:  "melocotones, nectarinas, ciruelas, sandia, melon, tomates, pepinos, pimientos, calabacines, berenjenas, judias verdes",
    8:  "sandia, melon, uvas tempranas, melocotones, higos, tomates, pimientos, berenjenas, calabacines, judias verdes",
    9:  "uvas, higos, peras, manzanas, granadas, tomates, pimientos, calabaza, berenjenas, champinones, judias verdes",
    10: "uvas, granadas, membrillos, manzanas, peras, calabaza, champinones, setas, espinacas, acelgas, col",
    11: "granadas, membrillos, manzanas, peras, kiwis, mandarinas, calabaza, setas, espinacas, acelgas, coliflor, brocoli",
    12: "naranjas, mandarinas, kiwis, peras, manzanas, granadas, espinacas, acelgas, col, coliflor, brocoli, puerros",
}

TABLE_CSS = """
body { font-family: Arial, Helvetica, sans-serif; font-size: 13px; color: #222; background: #fff; margin: 20px; }
h1   { font-size: 18px; font-weight: bold; margin: 0 0 4px 0; }
h2   { font-size: 14px; font-weight: bold; margin: 22px 0 6px 0; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
p    { margin: 0 0 18px 0; color: #555; font-size: 12px; }
table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
th    { background: #f0f0f0; font-weight: bold; text-align: left; padding: 7px 9px;
        border: 1px solid #bbb; font-size: 12px; }
td    { border: 1px solid #ccc; padding: 7px 9px; vertical-align: top; font-size: 12px; }
tr:nth-child(even) td { background: #fafafa; }
"""


def get_week_info():
    now  = datetime.now()
    iso  = now.isocalendar()
    return {
        "week_num": iso[1],
        "year":     iso[0],
        "month":    now.month,
        "date":     now.strftime("%d/%m/%Y"),
    }


def generate_meal_plan(week_info):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Variable de entorno ANTHROPIC_API_KEY no encontrada.")

    client  = anthropic.Anthropic(api_key=api_key)
    produce = SEASONAL_PRODUCE.get(week_info["month"], "frutas y verduras de temporada de la peninsula iberica")

    prompt = (
        f"Eres un nutricionista experto en cocina saludable para la peninsula iberica.\n"
        f"Genera el plan de comidas UNICO e IRREPETIBLE para la SEMANA ISO {week_info['week_num']} "
        f"del año {week_info['year']} (fecha de envio: {week_info['date']}).\n\n"
        f"RESTRICCIONES OBLIGATORIAS:\n"
        f"- Recetas UNICAMENTE preparables con microondas.\n"
        f"- Frutas y verduras de temporada peninsular: {produce}.\n"
        f"- PROHIBIDO: ultraprocesados, quesos fundidos, grasas saturadas, embutidos grasos.\n"
        f"- Sin repeticion de platos dentro de la misma semana.\n"
        f"- El plan debe ser completamente DIFERENTE al de cualquier semana anterior.\n\n"
        f"FORMATO: HTML puro y sobrio. Fondo blanco. Solo tablas con bordes simples.\n"
        f"NO uses gradientes, NO uses fondos de colores, NO uses emojis en texto de tabla.\n"
        f"CSS: unicamente el necesario inline para las tablas (border, padding, font).\n\n"
        f"ESTRUCTURA (en este orden exacto, nada mas):\n\n"
        f"<h1>Plan Semanal de Comidas Saludables - Semana {week_info['week_num']}/{week_info['year']}</h1>\n"
        f"<p>Fecha: {week_info['date']} | Solo microondas | Productos de temporada</p>\n\n"
        f"<h2>Menu Semanal</h2>\n"
        f"Tabla con columnas: DIA | DESAYUNO | COMIDA | CENA\n"
        f"Filas: Lunes a Domingo. Incluye la fecha de cada dia.\n\n"
        f"<h2>Recetas Principales</h2>\n"
        f"Tabla con columnas: PLATO | INGREDIENTES | PREPARACION EN MICROONDAS\n"
        f"Para las 7 comidas principales. Indica potencia (W) y tiempo en cada paso.\n\n"
        f"<h2>Lista de la Compra</h2>\n"
        f"Tabla con columnas: CATEGORIA | PRODUCTOS\n"
        f"Categorias: Verduras y Frutas | Proteinas | Cereales y Legumbres | Lacteos | Otros\n\n"
        f"DEVUELVE UNICAMENTE EL HTML, sin explicaciones previas ni posteriores."
    )

    print(f"Generando plan semana {week_info['week_num']}/{week_info['year']}...")
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8096,
        messages=[{"role": "user", "content": prompt}],
    )

    html = message.content[0].text
    if "```html" in html:
        html = html.split("```html")[1].split("```")[0].strip()
    elif "```" in html:
        html = html.split("```")[1].split("```")[0].strip()

    return html


def wrap_html_for_email(body_html):
    """Envuelve el cuerpo HTML generado con estilos de email."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
{TABLE_CSS}
</style>
</head>
<body>
{body_html}
</body>
</html>"""


def html_to_pdf(full_html):
    """Convierte HTML a bytes PDF usando xhtml2pdf."""
    pdf_buffer = io.BytesIO()
    result = pisa.CreatePDF(
        src=full_html.encode("utf-8"),
        dest=pdf_buffer,
        encoding="utf-8",
    )
    if result.err:
        raise RuntimeError(f"Error generando PDF (codigo {result.err}).")
    pdf_buffer.seek(0)
    return pdf_buffer.read()


def send_email(html_content, pdf_bytes, week_info):
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not password:
        raise RuntimeError("Variable de entorno GMAIL_APP_PASSWORD no encontrada.")

    send_date   = week_info["date"]
    subject     = f"Plan semanal de comidas de {send_date}"
    pdf_name    = f"plan_comidas_semana{week_info['week_num']}_{week_info['year']}.pdf"

    # Estructura: mixed > alternative (plain + html) + pdf adjunto
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL

    alt = MIMEMultipart("alternative")
    plain = (
        f"Plan Semanal de Comidas Saludables\n"
        f"Semana {week_info['week_num']}/{week_info['year']} - {send_date}\n\n"
        f"Abre este email en un cliente con soporte HTML para ver las tablas.\n"
        f"Tambien encontraras el plan en PDF adjunto.\n"
    )
    alt.attach(MIMEText(plain, "plain", "utf-8"))
    alt.attach(MIMEText(html_content, "html", "utf-8"))
    msg.attach(alt)

    # PDF adjunto
    pdf_part = MIMEBase("application", "pdf")
    pdf_part.set_payload(pdf_bytes)
    encoders.encode_base64(pdf_part)
    pdf_part.add_header("Content-Disposition", "attachment", filename=pdf_name)
    msg.attach(pdf_part)

    print(f"Enviando email a {RECEIVER_EMAIL}...")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as s:
        s.login(SENDER_EMAIL, password)
        s.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_bytes())

    print(f"Enviado: '{subject}' con adjunto '{pdf_name}'")


def main():
    try:
        week_info    = get_week_info()
        body_html    = generate_meal_plan(week_info)
        full_html    = wrap_html_for_email(body_html)
        pdf_bytes    = html_to_pdf(full_html)
        send_email(full_html, pdf_bytes, week_info)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
