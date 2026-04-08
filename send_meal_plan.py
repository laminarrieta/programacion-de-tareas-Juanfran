#!/usr/bin/env python3
"""
Plan Semanal de Comidas Saludables
Genera y envia por email un plan semanal de comidas usando la API de Claude.
Todas las recetas son preparables unicamente con microondas.
"""

import smtplib, os, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import anthropic

SENDER_EMAIL   = "laminarrieta@gmail.com"
RECEIVER_EMAIL = "laminarrieta@gmail.com"
SMTP_HOST      = "smtp.gmail.com"
SMTP_PORT      = 465


def get_current_season():
    m = datetime.now().month
    if m in [12, 1, 2]: return "invierno"
    if m in [3, 4, 5]:  return "primavera"
    if m in [6, 7, 8]:  return "verano"
    return "otono"


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


def generate_meal_plan():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Variable de entorno ANTHROPIC_API_KEY no encontrada.")
    client = anthropic.Anthropic(api_key=api_key)
    month     = datetime.now().month
    season    = get_current_season()
    produce   = SEASONAL_PRODUCE.get(month, "frutas y verduras de temporada de la peninsula iberica")
    send_date = datetime.now().strftime("%d/%m/%Y")
    prompt = (
        f"Eres un nutricionista experto en cocina saludable para la peninsula iberica.\n"
        f"Genera un plan semanal de comidas saludables completo para la semana del {send_date}.\n\n"
        f"RESTRICCIONES OBLIGATORIAS:\n"
        f"- Recetas UNICAMENTE con microondas (sin horno, vitroceramica, ni plancha).\n"
        f"- Frutas y verduras de temporada: {season}. Productos: {produce}.\n"
        f"- PROHIBIDO: ultraprocesados, quesos fundidos, productos grasientos, fiambres procesados, embutidos grasos.\n"
        f"- Cocina equilibrada, variada. Sin repeticion de platos durante la semana.\n\n"
        f"FORMATO: HTML completo y autocontenido con CSS MINIMO inline. "
        f"Paleta: verde (#2e7d32) y naranja (#e65100) sobre fondo blanco #ffffff.\n"
        f"USA ESTILOS INLINE DIRECTAMENTE EN CADA ELEMENTO, no bloques CSS largos.\n\n"
        f"ESTRUCTURA DEL HTML (en este orden exacto):\n"
        f"1. <head> con <style> muy breve (max 20 lineas de CSS basico).\n"
        f"2. <body> con un <div> contenedor.\n"
        f"3. Cabecera verde oscuro con titulo 'Plan Semanal de Comidas Saludables' y fecha {send_date}.\n"
        f"4. Parrafo introductorio motivador.\n"
        f"5. Tabla semanal: columnas DIA | DESAYUNO | COMIDA | CENA para Lunes a Domingo.\n"
        f"6. Seccion 'Recetas Destacadas' con las 7 comidas principales: ingredientes y pasos microondas (potencia W y tiempo).\n"
        f"7. Seccion 'Lista de la Compra': Frutas/verduras, Proteinas, Cereales/legumbres, Lacteos, Otros.\n"
        f"8. Pie de pagina motivador.\n\n"
        f"IMPORTANTE: Prioriza el contenido real sobre el CSS. Usa estilos simples."
    )
    print("Generando plan semanal con Claude...")
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
    return html, send_date


def send_email(html_content, send_date):
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not password:
        raise RuntimeError("Variable de entorno GMAIL_APP_PASSWORD no encontrada.")
    subject = f"Plan semanal de comidas de {send_date}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    plain_text = f"Plan Semanal de Comidas Saludables - {send_date}\n\nAbre en cliente HTML para ver el plan completo.\n"
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    print(f"Enviando email a {RECEIVER_EMAIL}...")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as s:
        s.login(SENDER_EMAIL, password)
        s.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_bytes())
    print(f"Email enviado: {subject}")


def main():
    try:
        html, date = generate_meal_plan()
        send_email(html, date)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
