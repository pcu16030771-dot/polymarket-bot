import requests
import json
import smtplib
import schedule
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============================================================
#  CONFIGURACION
# ============================================================
import os
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_DESTINO = "pcu16030771@gmail.com"
EMAIL_REMITENTE = "pcu16030771@gmail.com"
MONTO_SUGERIDO = 2

API_GAMMA = "https://gamma-api.polymarket.com/markets"

def formatear_volumen(v):
    if not v:
        return "$0"
    v = float(v)
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"

def obtener_mercados():
    try:
        params = {"active": "true", "closed": "false", "limit": 50, "order": "volume", "ascending": "false"}
        r = requests.get(API_GAMMA, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return []

def analizar_con_ia(pregunta, prob, volumen):
    try:
        prompt = f"""Eres un analista experto en mercados de prediccion. Analiza este mercado de Polymarket:

Pregunta: {pregunta}
Probabilidad actual: {prob}%
Volumen apostado: {volumen}

Responde SOLO con este formato exacto:
VEREDICTO: [SUBVALORADO / SOBREVALORADO / JUSTO]
CONFIANZA: [ALTA / MEDIA / BAJA]
APOSTAR_SI: [SI / NO]
RAZON: [Una sola oracion]"""

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 150,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=15
        )
        data = response.json()
        texto = data["content"][0]["text"]
        apostar = "APOSTAR_SI: SI" in texto and "CONFIANZA: ALTA" in texto
        return texto, apostar
    except Exception as e:
        return f"Error: {e}", False

def enviar_email(oportunidades):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎯 Polymarket Bot - {len(oportunidades)} oportunidad(es) encontrada(s)"
        msg["From"] = EMAIL_REMITENTE
        msg["To"] = EMAIL_DESTINO

        cuerpo = f"Hora del analisis: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        cuerpo += "="*50 + "\n"
        cuerpo += "OPORTUNIDADES DE ALTA CONFIANZA\n"
        cuerpo += "="*50 + "\n\n"

        for i, op in enumerate(oportunidades, 1):
            cuerpo += f"MERCADO {i}:\n"
            cuerpo += f"Pregunta: {op['pregunta']}\n"
            cuerpo += f"Probabilidad: {op['prob']}%\n"
            cuerpo += f"Volumen: {op['volumen']}\n"
            cuerpo += f"Analisis:\n{op['analisis']}\n"
            cuerpo += f"Monto sugerido: ${MONTO_SUGERIDO} USD\n"
            cuerpo += "\nEntra a polymarket.com para apostar.\n"
            cuerpo += "-"*50 + "\n\n"

        cuerpo += "RECUERDA: Esto es orientativo, no consejo financiero."

        msg.attach(MIMEText(cuerpo, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_REMITENTE, EMAIL_PASSWORD)
            server.sendmail(EMAIL_REMITENTE, EMAIL_DESTINO, msg.as_string())

        print(f"  Email enviado a {EMAIL_DESTINO}")
        return True
    except Exception as e:
        print(f"  Error enviando email: {e}")
        return False

def analisis_diario():
    print(f"\n{'='*50}")
    print(f"Analisis diario: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*50}")

    mercados = obtener_mercados()
    if not mercados:
        print("Sin mercados disponibles.")
        return

    zonas_inciertas = []
    for m in mercados:
        pregunta = m.get("question", "")
        if not pregunta:
            continue
        try:
            prices = json.loads(m.get("outcomePrices", "[]"))
            prob = round(float(prices[0]) * 100) if prices else 50
        except:
            prob = 50
        volumen = float(m.get("volume", 0) or 0)
        if 35 <= prob <= 65 and volumen > 500:
            zonas_inciertas.append({"pregunta": pregunta, "prob": prob, "volumen": formatear_volumen(volumen)})

    print(f"Mercados en zona incierta: {len(zonas_inciertas)}")

    oportunidades = []
    for m in zonas_inciertas[:10]:
        analisis, apostar = analizar_con_ia(m["pregunta"], m["prob"], m["volumen"])
        if apostar:
            oportunidades.append({
                "pregunta": m["pregunta"],
                "prob": m["prob"],
                "volumen": m["volumen"],
                "analisis": analisis
            })

    if oportunidades:
        print(f"Oportunidades de alta confianza: {len(oportunidades)}")
        enviar_email(oportunidades)
    else:
        print("Sin oportunidades de alta confianza hoy.")

def main():
    print("="*50)
    print("  POLYMARKET BOT FASE 4 - Notificaciones Email")
    print("  Analisis automatico cada dia a las 9:00 AM")
    print("="*50)

    # Correr analisis inmediatamente al iniciar
    analisis_diario()

    # Programar para cada dia a las 9:00 AM
    schedule.every().day.at("09:00").do(analisis_diario)

    print("\nBot activo. Esperando siguiente analisis...")
    print("Presiona Ctrl+C para detener.\n")

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()	