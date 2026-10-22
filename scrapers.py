import random
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus

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
        "priority": 1,
    },
    "Fnac": {
        "domains": ["fnac.com"],
        "icon": "📦",
        "account_url": "https://secure.fnac.com/identity/server/authenticate",
        "desc": "Precommandes + Click & Collect",
        "priority": 2,
    },
    "Micromania": {
        "domains": ["micromania.fr"],
        "icon": "🎮",
        "account_url": "https://www.micromania.fr/login",
        "desc": "Exclusivites gaming + cartes Pokemon",
        "priority": 2,
    },
    "Pokemon Center": {
        "domains": ["pokemoncenter.com"],
        "icon": "⚡",
        "account_url": "https://www.pokemoncenter.com/sign-in",
        "desc": "Boutique officielle - exclusivites Pokemon",
        "priority": 1,
    },
    "Cdiscount": {
        "domains": ["cdiscount.com"],
        "icon": "💰",
        "account_url": "https://clients.cdiscount.com/Account/Login",
        "desc": "Prix bas - ventes flash",
        "priority": 3,
    },
    "Cultura": {
        "domains": ["cultura.com"],
        "icon": "🎨",
        "account_url": "https://www.cultura.com/customer/account/login",
        "desc": "Cartes, coffrets, accessoires Pokemon",
        "priority": 2,
    },
    "Carrefour": {
        "domains": ["carrefour.fr"],
        "icon": "🏪",
        "account_url": "https://www.carrefour.fr/mon-compte/connexion",
        "desc": "ETB et coffrets en ligne + Drive",
        "priority": 3,
    },
    "Leclerc": {
        "domains": ["e.leclerc", "culture.leclerc"],
        "icon": "🛍️",
        "account_url": "https://www.e.leclerc/mon-compte",
        "desc": "Coffrets Pokemon + Drive",
        "priority": 3,
    },
    "Auchan": {
        "domains": ["auchan.fr"],
        "icon": "🔴",
        "account_url": "https://www.auchan.fr/login",
        "desc": "ETB et coffrets Pokemon",
        "priority": 3,
    },
    "JouéClub": {
        "domains": ["joueclub.fr"],
        "icon": "🧸",
        "account_url": "https://www.joueclub.fr/customer/account/login",
        "desc": "Specialiste jouets - coffrets et cartes Pokemon",
        "priority": 2,
    },
    "King Jouet": {
        "domains": ["king-jouet.com"],
        "icon": "👑",
        "account_url": "https://www.king-jouet.com/customer/account/login",
        "desc": "Jouets et jeux - ETB, displays Pokemon",
        "priority": 2,
    },
    "Smyths Toys": {
        "domains": ["smythstoys.com"],
        "icon": "🎪",
        "account_url": "https://www.smythstoys.com/fr/fr-fr/login",
        "desc": "Jouets - coffrets Pokemon, exclusivites",
        "priority": 2,
    },
    "Philibert": {
        "domains": ["philibert.net"],
        "icon": "🃏",
        "account_url": "https://www.philibert.net/mon-compte",
        "desc": "Specialiste jeux de cartes - precommandes Pokemon",
        "priority": 2,
    },
    "Cardmarket": {
        "domains": ["cardmarket.com"],
        "icon": "📊",
        "account_url": "https://www.cardmarket.com/en/Login",
        "desc": "Marketplace cartes a l'unite + scellees",
        "priority": 2,
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
    "JouéClub": _scrape_generic,
    "King Jouet": _scrape_generic,
    "Smyths Toys": _scrape_generic,
    "Philibert": _scrape_generic,
    "Cardmarket": _scrape_generic,
}


def get_site_priority(url):
    for site_key, site_info in SUPPORTED_SITES.items():
        if any(domain in url for domain in site_info["domains"]):
            return site_info.get("priority", 5)
    return 5


def sort_by_priority(products):
    return sorted(products, key=lambda p: get_site_priority(p["url"]))


def search_amazon(query, max_results=5):
    search_url = f"https://www.amazon.fr/s?k={quote_plus(query)}&i=toys"
    soup = _get_page(search_url)
    if not soup:
        return []

    results = []
    for div in soup.select("[data-component-type='s-search-result']"):
        asin = div.get("data-asin", "")
        if not asin:
            continue

        title_el = div.select_one("h2 a span") or div.select_one("h2 span")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)

        query_words = [w.lower() for w in query.split() if len(w) > 2]
        if not any(w in title.lower() for w in query_words):
            continue

        price_el = div.select_one("span.a-price-whole")
        price = None
        if price_el:
            price = price_el.get_text(strip=True).rstrip(",.") + " EUR"

        results.append({
            "url": f"https://www.amazon.fr/dp/{asin}",
            "name": title[:200],
            "price": price,
        })

        if len(results) >= max_results:
            break

    return results
