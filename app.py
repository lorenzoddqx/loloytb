import os
import json
import threading
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

from scrapers import check_product, SUPPORTED_SITES
from notifier import notify

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

PRODUCTS_FILE = "products.json"
ACCOUNTS_FILE = "accounts.json"
RELEASES_FILE = "releases.json"
HISTORY_FILE = "price_history.json"
CHECK_INTERVAL = max(30, int(os.getenv("CHECK_INTERVAL", "30")))

lock = threading.Lock()


def _load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_products():
    return _load_json(PRODUCTS_FILE)


def save_products(products):
    _save_json(PRODUCTS_FILE, products)


def load_accounts():
    return _load_json(ACCOUNTS_FILE)


def save_accounts(accounts):
    _save_json(ACCOUNTS_FILE, accounts)


def load_releases():
    releases = _load_json(RELEASES_FILE)
    if not releases:
        releases = DEFAULT_RELEASES
        _save_json(RELEASES_FILE, releases)
    return releases


def load_history():
    return _load_json(HISTORY_FILE)


def save_history(history):
    _save_json(HISTORY_FILE, history)


def record_price(url, price):
    if not price:
        return
    history = load_history()
    entry = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "price": price}
    if url not in [h["url"] for h in history]:
        history.append({"url": url, "prices": [entry]})
    else:
        for h in history:
            if h["url"] == url:
                if not h["prices"] or h["prices"][-1]["price"] != price:
                    h["prices"].append(entry)
                    if len(h["prices"]) > 500:
                        h["prices"] = h["prices"][-500:]
                break
    save_history(history)


DEFAULT_RELEASES = [
    {"name": "Pokemon 30 ans - Coffret Collection Premium", "date": "2026", "status": "rumeur", "category": "coffret"},
    {"name": "Pokemon 30 ans - ETB Elite Trainer Box", "date": "2026", "status": "rumeur", "category": "etb"},
    {"name": "Pokemon 30 ans - Display Booster", "date": "2026", "status": "rumeur", "category": "display"},
    {"name": "Pokemon 30 ans - Coffret Dresseur d'Elite", "date": "2026", "status": "rumeur", "category": "etb"},
    {"name": "Pokemon 30 ans - UPC Ultra Premium Collection", "date": "2026", "status": "rumeur", "category": "upc"},
]


def check_all_products():
    with lock:
        products = load_products()
    updated = False
    for product in products:
        result = check_product(product["url"])
        if result is None:
            continue
        was_in_stock = product.get("in_stock", False)
        now_in_stock = result["in_stock"]
        product["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        product["price"] = result["price"] or product.get("price")
        if result["title"] != "Produit inconnu":
            product["name"] = result["title"]
        record_price(product["url"], product.get("price"))
        if not was_in_stock and now_in_stock:
            notify(product["name"], product["url"], product["price"], "EN STOCK")
            product["in_stock"] = True
            updated = True
        elif was_in_stock and not now_in_stock:
            product["in_stock"] = False
            updated = True
        else:
            product["in_stock"] = now_in_stock
    with lock:
        save_products(products)


@app.route("/")
def index():
    products = load_products()
    accounts = load_accounts()
    releases = load_releases()
    in_stock_count = sum(1 for p in products if p.get("in_stock"))
    return render_template(
        "index.html",
        products=products,
        sites=SUPPORTED_SITES,
        accounts=accounts,
        releases=releases,
        in_stock_count=in_stock_count,
    )


@app.route("/add", methods=["POST"])
def add_product():
    url = request.form.get("url", "").strip()
    name = request.form.get("name", "").strip()
    if not url:
        flash("L'URL est obligatoire.", "error")
        return redirect(url_for("index"))

    site_found = None
    for site_key, site_info in SUPPORTED_SITES.items():
        if any(domain in url for domain in site_info["domains"]):
            site_found = site_key
            break

    if not site_found:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            site_found = parsed.netloc.replace("www.", "")
        else:
            flash("URL invalide.", "error")
            return redirect(url_for("index"))

    products = load_products()
    if any(p["url"] == url for p in products):
        flash("Ce produit est déjà suivi.", "error")
        return redirect(url_for("index"))

    product = {
        "url": url,
        "name": name or "Chargement...",
        "site": site_found,
        "in_stock": False,
        "price": None,
        "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_check": None,
    }
    products.append(product)
    with lock:
        save_products(products)

    flash(f"Produit ajouté ! Prochaine vérification dans {CHECK_INTERVAL}s.", "success")
    return redirect(url_for("index"))


@app.route("/remove", methods=["POST"])
def remove_product():
    url = request.form.get("url", "")
    products = load_products()
    products = [p for p in products if p["url"] != url]
    with lock:
        save_products(products)
    flash("Produit supprimé.", "success")
    return redirect(url_for("index"))


@app.route("/check-now", methods=["POST"])
def check_now():
    threading.Thread(target=check_all_products, daemon=True).start()
    flash("Vérification lancée !", "success")
    return redirect(url_for("index"))


@app.route("/accounts")
def accounts_page():
    accounts = load_accounts()
    return render_template("accounts.html", sites=SUPPORTED_SITES, accounts=accounts)


@app.route("/accounts/toggle", methods=["POST"])
def toggle_account():
    site = request.form.get("site", "")
    accounts = load_accounts()
    existing = next((a for a in accounts if a["site"] == site), None)
    if existing:
        existing["ready"] = not existing.get("ready", False)
    else:
        accounts.append({
            "site": site,
            "ready": True,
            "note": "",
        })
    save_accounts(accounts)
    flash(f"Compte {site} mis a jour.", "success")
    return redirect(url_for("accounts_page"))


@app.route("/accounts/note", methods=["POST"])
def update_account_note():
    site = request.form.get("site", "")
    note = request.form.get("note", "")
    accounts = load_accounts()
    existing = next((a for a in accounts if a["site"] == site), None)
    if existing:
        existing["note"] = note
    else:
        accounts.append({"site": site, "ready": False, "note": note})
    save_accounts(accounts)
    return redirect(url_for("accounts_page"))


@app.route("/releases")
def releases_page():
    releases = load_releases()
    return render_template("releases.html", releases=releases)


@app.route("/releases/add", methods=["POST"])
def add_release():
    name = request.form.get("name", "").strip()
    date = request.form.get("date", "").strip()
    category = request.form.get("category", "autre").strip()
    if not name:
        flash("Le nom est obligatoire.", "error")
        return redirect(url_for("releases_page"))
    releases = load_releases()
    releases.append({"name": name, "date": date or "TBA", "status": "rumeur", "category": category})
    _save_json(RELEASES_FILE, releases)
    flash("Sortie ajoutee.", "success")
    return redirect(url_for("releases_page"))


@app.route("/releases/remove", methods=["POST"])
def remove_release():
    name = request.form.get("name", "")
    releases = load_releases()
    releases = [r for r in releases if r["name"] != name]
    _save_json(RELEASES_FILE, releases)
    flash("Sortie supprimee.", "success")
    return redirect(url_for("releases_page"))


@app.route("/history")
def history_page():
    products = load_products()
    history = load_history()
    history_map = {h["url"]: h["prices"] for h in history}
    return render_template("history.html", products=products, history_map=history_map)


@app.route("/api/products")
def api_products():
    return jsonify(load_products())


@app.route("/api/history/<path:url>")
def api_history(url):
    history = load_history()
    for h in history:
        if h["url"] == url:
            return jsonify(h["prices"])
    return jsonify([])


scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(check_all_products, "interval", seconds=CHECK_INTERVAL)
scheduler.start()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
