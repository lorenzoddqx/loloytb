import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

from scrapers import check_product, SUPPORTED_SITES
from notifier import notify, get_active_channels, get_notification_log

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

PRODUCTS_FILE = "products.json"
ACCOUNTS_FILE = "accounts.json"
RELEASES_FILE = "releases.json"
HISTORY_FILE = "price_history.json"
CHECK_INTERVAL = max(30, int(os.getenv("CHECK_INTERVAL", "30")))

lock = threading.Lock()
_checking = threading.Event()


def _load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data
    except (json.JSONDecodeError, ValueError, OSError):
        return []


def _save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


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
    with lock:
        history = load_history()
        entry = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "price": price}
        found = False
        for h in history:
            if h["url"] == url:
                found = True
                if not h["prices"] or h["prices"][-1]["price"] != price:
                    h["prices"].append(entry)
                    if len(h["prices"]) > 500:
                        h["prices"] = h["prices"][-500:]
                break
        if not found:
            history.append({"url": url, "prices": [entry]})
        save_history(history)


DEFAULT_RELEASES = [
    {"name": "Pokemon 30 ans - Coffret Collection Premium", "date": "2026", "status": "rumeur", "category": "coffret"},
    {"name": "Pokemon 30 ans - ETB Elite Trainer Box", "date": "2026", "status": "rumeur", "category": "etb"},
    {"name": "Pokemon 30 ans - Display Booster", "date": "2026", "status": "rumeur", "category": "display"},
    {"name": "Pokemon 30 ans - Coffret Dresseur d'Elite", "date": "2026", "status": "rumeur", "category": "etb"},
    {"name": "Pokemon 30 ans - UPC Ultra Premium Collection", "date": "2026", "status": "rumeur", "category": "upc"},
]


def _check_single(product_snapshot):
    url = product_snapshot["url"]
    return url, check_product(url)


def check_all_products():
    if _checking.is_set():
        return
    _checking.set()
    try:
        with lock:
            products = load_products()
        if not products:
            return
        start = time.monotonic()
        print(f"[{datetime.now():%H:%M:%S}] Checking {len(products)} products...")
        results = {}
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(_check_single, p): p["url"] for p in products}
            for future in as_completed(futures):
                try:
                    url, result = future.result()
                    results[url] = result
                except Exception as e:
                    print(f"  > Check failed for {futures[future]}: {e}")
        for product in products:
            result = results.get(product["url"])
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
            elif was_in_stock and not now_in_stock:
                product["in_stock"] = False
            else:
                product["in_stock"] = now_in_stock
        with lock:
            save_products(products)
        elapsed = time.monotonic() - start
        print(f"[{datetime.now():%H:%M:%S}] Done in {elapsed:.1f}s")
    finally:
        _checking.clear()


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
        check_interval=CHECK_INTERVAL,
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

    with lock:
        products = load_products()
        if any(p["url"] == url for p in products):
            flash("Ce produit est deja suivi.", "error")
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
        save_products(products)

    flash(f"Produit ajoute ! Prochaine verification dans {CHECK_INTERVAL}s.", "success")
    return redirect(url_for("index"))


@app.route("/remove", methods=["POST"])
def remove_product():
    url = request.form.get("url", "")
    with lock:
        products = load_products()
        products = [p for p in products if p["url"] != url]
        save_products(products)
    flash("Produit supprime.", "success")
    return redirect(url_for("index"))


@app.route("/check-now", methods=["POST"])
def check_now():
    if _checking.is_set():
        flash("Une verification est deja en cours...", "error")
    else:
        threading.Thread(target=check_all_products, daemon=True).start()
        flash("Verification lancee !", "success")
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
        accounts.append({"site": site, "ready": True, "note": ""})
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


@app.route("/settings")
def settings_page():
    channels = get_active_channels()
    log = get_notification_log()
    return render_template(
        "settings.html",
        channels=channels,
        notification_log=log[-20:],
        check_interval=CHECK_INTERVAL,
    )


@app.route("/test-notification", methods=["POST"])
def test_notification():
    notify("Test Notification", "https://example.com", "0.00 EUR", "TEST")
    flash("Notification de test envoyee sur tous les canaux actifs.", "success")
    return redirect(url_for("settings_page"))


@app.route("/api/products")
def api_products():
    return jsonify(load_products())


@app.route("/api/status")
def api_status():
    products = load_products()
    return jsonify({
        "status": "running",
        "products_count": len(products),
        "in_stock_count": sum(1 for p in products if p.get("in_stock")),
        "check_interval": CHECK_INTERVAL,
        "checking_now": _checking.is_set(),
        "channels": get_active_channels(),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/history/<path:url>")
def api_history(url):
    history = load_history()
    for h in history:
        if h["url"] == url:
            return jsonify(h["prices"])
    return jsonify([])


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page introuvable"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="Erreur interne du serveur"), 500


scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(check_all_products, "interval", seconds=CHECK_INTERVAL, id="main_check", replace_existing=True)

if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler.start()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
