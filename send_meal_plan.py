#!/usr/bin/env python3
"""
Plan Semanal de Comidas Saludables
Genera y envía por email un plan semanal de comidas usando la API de Claude.
Incluye PDF adjunto. Todas las recetas son preparables únicamente con microondas.
"""

import smtplib, os, io, sys, re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import anthropic
from fpdf import FPDF
from fpdf.enums import XPos, YPos

SENDER_EMAIL    = "laminarrieta@gmail.com"
RECEIVER_EMAILS = ["laminarrieta@gmail.com", "maite.ruffo@gmail.com"]
SMTP_HOST       = "smtp.gmail.com"
SMTP_PORT       = 465

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
body  { font-family: Arial, Helvetica, sans-serif; font-size: 13px; color: #222; background: #fff; margin: 24px 30px; }
h1    { font-size: 18px; font-weight: bold; margin: 0 0 4px 0; }
h2    { font-size: 14px; font-weight: bold; margin: 24px 0 6px 0;
        border-bottom: 1px solid #ccc; padding-bottom: 4px; }
p     { margin: 0 0 16px 0; color: #555; font-size: 12px; }
table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
th    { background: #ebebeb; font-weight: bold; text-align: left;
        padding: 7px 10px; border: 1px solid #bbb; font-size: 12px; }
td    { border: 1px solid #ccc; padding: 7px 10px; vertical-align: top; font-size: 12px; }
tr:nth-child(even) td { background: #f8f8f8; }
"""


# ─── helpers ────────────────────────────────────────────────────────────────

def get_week_info():
    now = datetime.now()
    iso = now.isocalendar()
    return {"week_num": iso[1], "year": iso[0], "month": now.month,
            "date": now.strftime("%d/%m/%Y")}


def strip_tags(text):
    """Elimina etiquetas HTML y decodifica entidades básicas."""
    text = re.sub(r"<[^>]+>", " ", text)
    for ent, ch in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                    ("&nbsp;", " "), ("&aacute;", "á"), ("&eacute;", "é"),
                    ("&iacute;", "í"), ("&oacute;", "ó"), ("&uacute;", "ú"),
                    ("&ntilde;", "ñ"), ("&Aacute;", "Á"), ("&Eacute;", "É"),
                    ("&Iacute;", "Í"), ("&Oacute;", "Ó"), ("&Uacute;", "Ú"),
                    ("&Ntilde;", "Ñ"), ("&#243;", "ó"), ("&#233;", "é"),
                    ("&#237;", "í"), ("&#250;", "ú"), ("&#225;", "á"),
                    ("&#241;", "ñ")]:
        text = text.replace(ent, ch)
    return re.sub(r"\s+", " ", text).strip()


# ─── generacion de contenido ──────────────────────────────────────────────

def generate_meal_plan(week_info):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY no encontrada.")

    client  = anthropic.Anthropic(api_key=api_key)
    produce = SEASONAL_PRODUCE.get(week_info["month"],
                                   "frutas y verduras de temporada de la peninsula iberica")

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
        f"FORMATO: HTML sobrio. Sin gradientes ni fondos de colores. Fondo blanco, texto negro.\n"
        f"CSS: minimo inline, solo para tablas (border:1px solid #ccc, padding:7px).\n\n"
        f"ESTRUCTURA (este orden exacto, nada mas):\n\n"
        f"<h1>Plan Semanal de Comidas - Semana {week_info['week_num']}/{week_info['year']}</h1>\n"
        f"<p>Fecha: {week_info['date']} | Solo microondas | Productos de temporada</p>\n\n"
        f"<h2>Menu Semanal</h2>\n"
        f"Tabla: columnas DIA | DESAYUNO | COMIDA | CENA. Filas Lunes-Domingo con fecha.\n\n"
        f"<h2>Recetas Principales</h2>\n"
        f"Tabla: columnas PLATO | INGREDIENTES | PREPARACION EN MICROONDAS (potencia W y tiempo).\n"
        f"Una fila por cada comida principal (las 7 del menu).\n\n"
        f"<h2>Lista de la Compra</h2>\n"
        f"Tabla: columnas CATEGORIA | PRODUCTOS.\n"
        f"Categorias: Verduras y Frutas | Proteinas | Cereales y Legumbres | Lacteos | Otros\n\n"
        f"DEVUELVE UNICAMENTE EL HTML. Sin texto antes ni despues."
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


# ─── generacion de PDF con fpdf2 ─────────────────────────────────────────

def parse_tables_from_html(html):
    """Extrae tablas del HTML como lista de listas (filas x celdas)."""
    tables = []
    for table_match in re.finditer(r"<table[^>]*>(.*?)</table>", html, re.S | re.I):
        rows = []
        for row_match in re.finditer(r"<tr[^>]*>(.*?)</tr>", table_match.group(1), re.S | re.I):
            cells = []
            for cell in re.finditer(r"<t[hd][^>]*>(.*?)</t[hd]>", row_match.group(1), re.S | re.I):
                cells.append(strip_tags(cell.group(1)))
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def parse_headings_from_html(html):
    """Extrae h1, h2 y p del HTML en orden."""
    elements = []
    for m in re.finditer(r"<(h1|h2|p)[^>]*>(.*?)</\1>", html, re.S | re.I):
        elements.append((m.group(1).lower(), strip_tags(m.group(2))))
    return elements


def build_pdf(html, week_info):
    """Construye el PDF a partir del HTML generado."""
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Título
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_fill_color(240, 240, 240)
    title = f"Plan Semanal de Comidas - Semana {week_info['week_num']}/{week_info['year']}"
    pdf.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C", fill=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Fecha: {week_info['date']}  |  Solo microondas  |  Productos de temporada",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # Secciones: combinar headings y tablas
    headings    = parse_headings_from_html(html)
    tables      = parse_tables_from_html(html)
    h2_headings = [h for h in headings if h[0] == "h2"]
    table_idx   = 0

    for h2_title, _ in h2_headings:
        pdf.set_font("Helvetica", "B", 11)
        pdf.ln(3)
        pdf.cell(0, 8, h2_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(180, 180, 180)
        pdf.set_line_width(0.3)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(3)

        if table_idx >= len(tables):
            continue

        rows = tables[table_idx]
        table_idx += 1

        if not rows:
            continue

        usable_w = pdf.w - pdf.l_margin - pdf.r_margin
        n_cols   = max(len(r) for r in rows)

        if n_cols == 4:
            col_w = [usable_w * 0.13, usable_w * 0.29, usable_w * 0.29, usable_w * 0.29]
        elif n_cols == 3:
            col_w = [usable_w * 0.22, usable_w * 0.30, usable_w * 0.48]
        elif n_cols == 2:
            col_w = [usable_w * 0.25, usable_w * 0.75]
        else:
            col_w = [usable_w / n_cols] * n_cols

        for r_idx, row in enumerate(rows):
            is_header = (r_idx == 0)

            row_height = 0
            for c_idx, cell_text in enumerate(row):
                if c_idx >= n_cols:
                    break
                w = col_w[c_idx] if c_idx < len(col_w) else col_w[-1]
                pdf.set_font("Helvetica", "B" if is_header else "", 8)
                lines = pdf.multi_cell(w, 5, cell_text, dry_run=True, output="LINES")
                cell_h = len(lines) * 5 + 4
                row_height = max(row_height, cell_h)

            row_height = max(row_height, 10)

            if pdf.get_y() + row_height > pdf.h - pdf.b_margin:
                pdf.add_page()

            for c_idx, cell_text in enumerate(row):
                if c_idx >= n_cols:
                    break
                w = col_w[c_idx] if c_idx < len(col_w) else col_w[-1]

                pdf.set_font("Helvetica", "B" if is_header else "", 8)
                if is_header:
                    pdf.set_fill_color(220, 220, 220)
                elif r_idx % 2 == 0:
                    pdf.set_fill_color(248, 248, 248)
                else:
                    pdf.set_fill_color(255, 255, 255)

                pdf.set_xy(pdf.l_margin + sum(col_w[:c_idx]), pdf.get_y())
                pdf.multi_cell(w, 5, cell_text, border=1, fill=True,
                               max_line_height=5,
                               new_x=XPos.RIGHT if c_idx < n_cols - 1 else XPos.LMARGIN,
                               new_y=YPos.TOP   if c_idx < n_cols - 1 else YPos.NEXT)

        pdf.ln(2)

    return bytes(pdf.output())


# ─── email ───────────────────────────────────────────────────────────────────

def wrap_html_email(body_html):
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<style>
{TABLE_CSS}
</style>
</head><body>
{body_html}
</body></html>"""


def send_email(html_content, pdf_bytes, week_info):
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not password:
        raise RuntimeError("GMAIL_APP_PASSWORD no encontrada.")

    send_date = week_info["date"]
    subject   = f"Plan semanal de comidas de {send_date}"
    pdf_name  = f"plan_comidas_semana{week_info['week_num']}_{week_info['year']}.pdf"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = ", ".join(RECEIVER_EMAILS)

    alt = MIMEMultipart("alternative")
    plain = (f"Plan Semanal de Comidas - Semana {week_info['week_num']}/{week_info['year']} "
             f"- {send_date}\n\nEncontraras el plan en PDF adjunto.\n")
    alt.attach(MIMEText(plain, "plain", "utf-8"))
    alt.attach(MIMEText(html_content, "html", "utf-8"))
    msg.attach(alt)

    pdf_part = MIMEBase("application", "pdf")
    pdf_part.set_payload(pdf_bytes)
    encoders.encode_base64(pdf_part)
    pdf_part.add_header("Content-Disposition", "attachment", filename=pdf_name)
    msg.attach(pdf_part)

    print(f"Enviando email a: {', '.join(RECEIVER_EMAILS)}...")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as s:
        s.login(SENDER_EMAIL, password)
        s.sendmail(SENDER_EMAIL, RECEIVER_EMAILS, msg.as_bytes())

    print(f"Enviado: '{subject}'  |  Adjunto: '{pdf_name}'")


# ─── main ────────────────────────────────────────────────────────────────────

def main():
    try:
        week_info = get_week_info()
        body_html = generate_meal_plan(week_info)
        full_html = wrap_html_email(body_html)
        pdf_bytes = build_pdf(body_html, week_info)
        send_email(full_html, pdf_bytes, week_info)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
