import random
import requests
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

SUPPORTED_SITES = {
    "Amazon": {
        "domains": ["amazon.fr", "amazon.com", "amazon.de", "amazon.co.uk"],
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
        "account_url": "https://www.e.leclerc/auth/realms/LeclercDrive",
        "desc": "Coffrets Pokemon + Drive",
    },
    "Auchan": {
        "domains": ["auchan.fr"],
        "icon": "🔴",
        "account_url": "https://www.auchan.fr/login",
        "desc": "ETB et coffrets Pokemon",
    },
    "Philibert": {
        "domains": ["phfrancais.com", "philibert.fr"],
        "icon": "🃏",
        "account_url": "https://www.phfrancais.com/mon-compte",
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


def _get_page(url):
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except requests.RequestException as e:
        print(f"  ✗ Erreur réseau: {e}")
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
    ])
    in_stock = False
    avail_div = soup.find("div", id="availability")
    if avail_div:
        text = avail_div.get_text(strip=True).lower()
        if any(w in text for w in ["en stock", "in stock", "disponible"]):
            in_stock = True
    if not in_stock:
        if soup.find("input", {"id": "add-to-cart-button"}):
            in_stock = True
    return {"title": title, "price": price, "in_stock": in_stock}


def _scrape_fnac(url):
    soup = _get_page(url)
    if not soup:
        return None
    title_tag = soup.find("h1", class_="f-productHeader-Title")
    title = title_tag.get_text(strip=True) if title_tag else "Produit inconnu"
    price = _find_price(soup, [
        ("span", {"class": "f-productHeader-Price"}),
        ("span", {"class": "userPrice"}),
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
        elif "disponible" in text or "stock" in text:
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
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Produit inconnu"
    price = _find_price(soup, [
        ("span", {"class": "price"}),
        ("meta", {"property": "product:price:amount"}),
    ])
    page_text = soup.get_text().lower()
    in_stock = not any(w in page_text for w in [
        "indisponible", "out of stock", "rupture", "currently unavailable",
    ])
    return {"title": title, "price": price, "in_stock": in_stock}


def _find_price(soup, selectors):
    for tag, attrs in selectors:
        el = soup.find(tag, attrs)
        if el:
            if tag == "meta":
                content = el.get("content", "")
                if content:
                    return content + " €"
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
