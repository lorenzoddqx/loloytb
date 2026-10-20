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
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "120"))

lock = threading.Lock()


def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        return []
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)


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
        if not was_in_stock and now_in_stock:
            notify(product["name"], product["url"], product["price"], "EN STOCK")
            product["in_stock"] = True
            updated = True
        elif was_in_stock and not now_in_stock:
            product["in_stock"] = False
            updated = True
        elif now_in_stock != was_in_stock:
            product["in_stock"] = now_in_stock
            updated = True
        else:
            product["in_stock"] = now_in_stock
    with lock:
        save_products(products)


@app.route("/")
def index():
    products = load_products()
    return render_template("index.html", products=products, sites=SUPPORTED_SITES)


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
        flash("Site non supporté. Sites supportés : " + ", ".join(SUPPORTED_SITES.keys()), "error")
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


@app.route("/api/products")
def api_products():
    return jsonify(load_products())


scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(check_all_products, "interval", seconds=CHECK_INTERVAL)
scheduler.start()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
