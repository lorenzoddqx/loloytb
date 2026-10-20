import smtplib
import os
import threading
from datetime import datetime
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
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

_notification_log = []
_log_lock = threading.Lock()
MAX_LOG_ENTRIES = 200


def get_notification_log():
    with _log_lock:
        return list(_notification_log)


def _log(channel, product_name, success, detail=""):
    entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "channel": channel,
        "product": product_name,
        "success": success,
        "detail": detail,
    }
    with _log_lock:
        _notification_log.append(entry)
        if len(_notification_log) > MAX_LOG_ENTRIES:
            _notification_log.pop(0)


def get_active_channels():
    channels = []
    if DISCORD_WEBHOOK_URL:
        channels.append("Discord")
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        channels.append("Telegram")
    if EMAIL_SENDER and EMAIL_PASSWORD and EMAIL_RECEIVER:
        channels.append("Email")
    return channels


def send_discord(product_name, url, price, status):
    if not DISCORD_WEBHOOK_URL:
        return
    color = 0x00FF00 if status == "EN STOCK" else 0xFF9900
    payload = {
        "content": f"@everyone **{status}** — {product_name}",
        "embeds": [{
            "title": f"{status} — {product_name}",
            "url": url,
            "color": color,
            "fields": [
                {"name": "Prix", "value": price or "Non disponible", "inline": True},
                {"name": "Statut", "value": status, "inline": True},
                {"name": "Lien rapide", "value": f"[Acheter maintenant]({url})", "inline": False},
            ],
            "footer": {"text": "Restock Tracker"},
            "timestamp": datetime.utcnow().isoformat(),
        }]
    }
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        ok = resp.status_code == 204
        _log("Discord", product_name, ok, f"HTTP {resp.status_code}")
    except Exception as e:
        _log("Discord", product_name, False, str(e))


def send_telegram(product_name, url, price, status):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    icon = "\U0001f7e2" if status == "EN STOCK" else "\U0001f7e0"
    text = (
        f"{icon} <b>{status}</b>\n\n"
        f"<b>{product_name}</b>\n"
        f"Prix: {price or 'Non disponible'}\n\n"
        f'<a href="{url}">Acheter maintenant</a>'
    )
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(api_url, json=payload, timeout=10)
        ok = resp.status_code == 200
        _log("Telegram", product_name, ok, f"HTTP {resp.status_code}")
    except Exception as e:
        _log("Telegram", product_name, False, str(e))


def send_email(product_name, url, price, status):
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"ALERTE {status} — {product_name}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    html = f"""\
<html><body style="font-family:-apple-system,sans-serif;padding:20px;background:#0f0f0f;color:#eee;">
<div style="max-width:500px;margin:0 auto;background:#1a1a2e;border-radius:12px;padding:24px;border:1px solid #2a2a3e;">
<h2 style="color:#e63946;margin:0 0 16px;">ALERTE {status}</h2>
<p style="font-size:18px;margin:0 0 8px;"><strong>{product_name}</strong></p>
<p style="margin:0 0 20px;color:#888;">Prix: <strong style="color:#2ecc71;">{price or 'Non disponible'}</strong></p>
<p><a href="{url}" style="background:#e63946;color:white;padding:14px 28px;
text-decoration:none;border-radius:8px;display:inline-block;font-weight:600;font-size:16px;">
Acheter maintenant</a></p>
</div>
</body></html>"""
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        _log("Email", product_name, True)
    except Exception as e:
        _log("Email", product_name, False, str(e))


def notify(product_name, url, price, status):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{ts}] {'='*46}")
    print(f"  ALERTE: {status} — {product_name}")
    print(f"  Prix: {price or 'N/A'}")
    print(f"  Lien: {url}")
    print(f"  {'='*46}")

    threads = []
    for fn in (send_discord, send_telegram, send_email):
        t = threading.Thread(target=fn, args=(product_name, url, price, status), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=15)
