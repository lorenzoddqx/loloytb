import smtplib
import os
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))


def send_discord(product_name, url, price, status):
    if not DISCORD_WEBHOOK_URL:
        return
    color = 0x00FF00 if status == "EN STOCK" else 0xFF9900
    payload = {
        "embeds": [{
            "title": f"{status} — {product_name}",
            "url": url,
            "color": color,
            "fields": [
                {"name": "Prix", "value": price or "Non disponible", "inline": True},
                {"name": "Statut", "value": status, "inline": True},
            ],
            "footer": {"text": "Restock Tracker"},
        }]
    }
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code == 204:
            print(f"  > Notification Discord envoyee pour {product_name}")
        else:
            print(f"  > Erreur Discord: {resp.status_code}")
    except Exception as e:
        print(f"  > Erreur Discord: {e}")


def send_email(product_name, url, price, status):
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"ALERTE {status} — {product_name}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    html = f"""\
<html><body style="font-family:sans-serif;padding:20px;">
<h2 style="color:#e63946;">ALERTE {status}</h2>
<p style="font-size:18px;"><strong>{product_name}</strong></p>
<p>Prix: <strong>{price or 'Non disponible'}</strong></p>
<p><a href="{url}" style="background:#e63946;color:white;padding:12px 24px;
text-decoration:none;border-radius:6px;display:inline-block;">
Voir le produit</a></p>
</body></html>"""
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        print(f"  > Email envoye pour {product_name}")
    except Exception as e:
        print(f"  > Erreur email: {e}")


def notify(product_name, url, price, status):
    print(f"\n{'='*50}")
    print(f"  ALERTE: {status} — {product_name}")
    print(f"  Prix: {price or 'N/A'}")
    print(f"  Lien: {url}")
    print(f"{'='*50}")
    send_discord(product_name, url, price, status)
    send_email(product_name, url, price, status)
