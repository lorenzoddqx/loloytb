import random
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

SUPPORTED_SITES = {
    "Amazon": {
        "domains": ["amazon.fr", "amazon.com", "amazon.de", "amazon.co.uk", "amazon.es", "amazon.it"],
        "icon": "🛒",
        "account_url": "https://www.amazon.fr/ap/signin",
        "desc": "Marketplace general - ETB, coffrets, boosters",
    },
    "Fnac": {
        "domains": ["fnac.com"],
        "icon": "📦",
        "account_url": "https://secure.fnac.com/identity/server/authenticate",
        "desc": "Precommandes + Click & Collect",
    },
    "Micromania": {
        "domains": ["micromania.fr"],
        "icon": "🎮",
        "account_url": "https://www.micromania.fr/login",
        "desc": "Exclusivites gaming + cartes Pokemon",
    },
    "Pokemon Center": {
        "domains": ["pokemoncenter.com"],
        "icon": "⚡",
        "account_url": "https://www.pokemoncenter.com/sign-in",
        "desc": "Boutique officielle - exclusivites Pokemon",
    },
    "Cdiscount": {
        "domains": ["cdiscount.com"],
        "icon": "💰",
        "account_url": "https://clients.cdiscount.com/Account/Login",
        "desc": "Prix bas - ventes flash",
    },
    "Cultura": {
        "domains": ["cultura.com"],
        "icon": "🎨",
        "account_url": "https://www.cultura.com/customer/account/login",
        "desc": "Cartes, coffrets, accessoires Pokemon",
    },
    "Carrefour": {
        "domains": ["carrefour.fr"],
        "icon": "🏪",
        "account_url": "https://www.carrefour.fr/mon-compte/connexion",
        "desc": "ETB et coffrets en ligne + Drive",
    },
    "Leclerc": {
        "domains": ["e.leclerc", "culture.leclerc"],
        "icon": "🛍️",
        "account_url": "https://www.e.leclerc/mon-compte",
        "desc": "Coffrets Pokemon + Drive",
    },
    "Auchan": {
        "domains": ["auchan.fr"],
        "icon": "🔴",
        "account_url": "https://www.auchan.fr/login",
        "desc": "ETB et coffrets Pokemon",
    },
    "Philibert": {
        "domains": ["philibert.net"],
        "icon": "🃏",
        "account_url": "https://www.philibert.net/mon-compte",
        "desc": "Specialiste jeux de cartes - precommandes Pokemon",
    },
    "Pokemart": {
        "domains": ["pokemart.fr"],
        "icon": "📮",
        "account_url": "https://www.pokemart.fr/connexion",
        "desc": "Boutique specialisee Pokemon FR",
    },
    "Cardmarket": {
        "domains": ["cardmarket.com"],
        "icon": "📊",
        "account_url": "https://www.cardmarket.com/en/Login",
        "desc": "Marketplace cartes a l'unite + scellees",
    },
}

_session = requests.Session()
_session.headers.update({
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
})


def _get_page(url, retries=2):
    for attempt in range(retries + 1):
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            resp = _session.get(url, headers=headers, timeout=12, allow_redirects=True)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as e:
            if attempt < retries:
                time.sleep(1 + attempt)
                continue
            print(f"  [ERR] {urlparse(url).netloc}: {e}")
            return None


def check_product(url):
    for site_key, site_info in SUPPORTED_SITES.items():
        if any(domain in url for domain in site_info["domains"]):
            scraper = SCRAPERS.get(site_key, _scrape_generic)
            return scraper(url)
    return _scrape_generic(url)


def _scrape_amazon(url):
    soup = _get_page(url)
    if not soup:
        return None
    title_tag = soup.find("span", id="productTitle")
    title = title_tag.get_text(strip=True) if title_tag else "Produit inconnu"

    price = _find_price(soup, [
        ("span", {"class": "a-price-whole"}),
        ("span", {"id": "priceblock_ourprice"}),
        ("span", {"id": "priceblock_dealprice"}),
        ("span", {"class": "a-offscreen"}),
    ])

    in_stock = False
    avail_div = soup.find("div", id="availability")
    if avail_div:
        text = avail_div.get_text(strip=True).lower()
        if any(w in text for w in ["en stock", "in stock", "disponible", "livraison"]):
            in_stock = True
        if any(w in text for w in ["indisponible", "unavailable", "rupture"]):
            in_stock = False
    if not in_stock:
        if soup.find("input", {"id": "add-to-cart-button"}) or soup.find("input", {"id": "buy-now-button"}):
            in_stock = True

    return {"title": title, "price": price, "in_stock": in_stock}


def _scrape_fnac(url):
    soup = _get_page(url)
    if not soup:
        return None
    title_tag = soup.find("h1", class_="f-productHeader-Title") or soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Produit inconnu"

    price = _find_price(soup, [
        ("span", {"class": "f-productHeader-Price"}),
        ("span", {"class": "userPrice"}),
        ("span", {"class": "checkedProduct__price"}),
    ])

    in_stock = False
    buy_btn = soup.find("button", class_="f-addToCart")
    if buy_btn:
        in_stock = True
    avail = soup.find("div", class_="f-productHeader-Availability")
    if avail:
        text = avail.get_text(strip=True).lower()
        if "indisponible" in text or "rupture" in text:
            in_stock = False
        elif "disponible" in text or "stock" in text or "livraison" in text:
            in_stock = True

    return {"title": title, "price": price, "in_stock": in_stock}


def _scrape_micromania(url):
    soup = _get_page(url)
    if not soup:
        return None
    title_tag = soup.find("h1", class_="product-name") or soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Produit inconnu"

    price = _find_price(soup, [
        ("span", {"class": "price"}),
        ("span", {"class": "product-price"}),
    ])

    in_stock = False
    add_btn = soup.find("button", {"id": "add-to-cart"}) or soup.find("button", class_="add-to-cart")
    if add_btn:
        disabled = add_btn.get("disabled")
        in_stock = disabled is None

    return {"title": title, "price": price, "in_stock": in_stock}


def _scrape_generic(url):
    soup = _get_page(url)
    if not soup:
        return None

    title = _extract_title(soup)
    price = _extract_price_generic(soup)
    in_stock = _detect_stock_generic(soup)

    return {"title": title, "price": price, "in_stock": in_stock}


def _extract_title(soup):
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)[:200]
    title = soup.find("title")
    if title:
        return title.get_text(strip=True)[:200]
    return "Produit inconnu"


def _extract_price_generic(soup):
    schema_price = soup.find("meta", {"property": "product:price:amount"})
    if schema_price and schema_price.get("content"):
        currency = soup.find("meta", {"property": "product:price:currency"})
        sym = "EUR" if not currency else currency.get("content", "EUR")
        return f"{schema_price['content']} {sym}"

    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or ""
        if '"price"' in text:
            try:
                import json
                data = json.loads(text)
                if isinstance(data, list):
                    data = data[0]
                offers = data.get("offers", data)
                if isinstance(offers, list):
                    offers = offers[0]
                p = offers.get("price") or offers.get("lowPrice")
                if p:
                    c = offers.get("priceCurrency", "EUR")
                    return f"{p} {c}"
            except (json.JSONDecodeError, AttributeError, KeyError, TypeError, IndexError):
                pass

    return _find_price(soup, [
        ("span", {"class": "price"}),
        ("span", {"class": "product-price"}),
        ("span", {"class": "current-price"}),
        ("div", {"class": "price"}),
    ])


def _detect_stock_generic(soup):
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or ""
        if '"availability"' in text.lower():
            lower = text.lower()
            if "instock" in lower or "instoreonly" in lower or "preorder" in lower:
                return True
            if "outofstock" in lower or "discontinued" in lower:
                return False

    page_text = soup.get_text().lower()

    out_words = [
        "indisponible", "out of stock", "rupture de stock", "currently unavailable",
        "en rupture", "produit indisponible", "sold out", "epuise",
        "article indisponible", "momentanement indisponible",
    ]
    if any(w in page_text for w in out_words):
        return False

    in_words = [
        "ajouter au panier", "add to cart", "add to bag",
        "en stock", "in stock", "disponible", "acheter",
        "commander", "livraison disponible",
    ]
    if any(w in page_text for w in in_words):
        return True

    if soup.find("button", string=lambda t: t and "panier" in t.lower()):
        return True
    if soup.find("button", string=lambda t: t and "cart" in t.lower()):
        return True

    return False


def _find_price(soup, selectors):
    for tag, attrs in selectors:
        el = soup.find(tag, attrs)
        if el:
            if tag == "meta":
                content = el.get("content", "")
                if content:
                    return content + " EUR"
            text = el.get_text(strip=True)
            if any(c.isdigit() for c in text):
                return text
    return None


SCRAPERS = {
    "Amazon": _scrape_amazon,
    "Fnac": _scrape_fnac,
    "Micromania": _scrape_micromania,
    "Pokemon Center": _scrape_generic,
    "Cdiscount": _scrape_generic,
    "Cultura": _scrape_generic,
    "Carrefour": _scrape_generic,
    "Leclerc": _scrape_generic,
    "Auchan": _scrape_generic,
    "Philibert": _scrape_generic,
    "Pokemart": _scrape_generic,
    "Cardmarket": _scrape_generic,
}
