import argparse
import asyncio
import json
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus, unquote, urljoin, urlparse

import gspread
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import Browser, Page, async_playwright


DEFAULT_QUERIES = [
    {"keyword": "centro estetico", "city": "Milano"},
    {"keyword": "beauty studio", "city": "Milano"},
    {"keyword": "beauty saloon", "city": "Milano"},
    {"keyword": "estetista", "city": "Gallarate"},
    {"keyword": "pasticceria artigianale", "city": "Milano"},
    {"keyword": "parrucchiere", "city": "Milano"},
    {"keyword": "psicologo", "city": "Milano"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.IGNORECASE)


@dataclass
class BusinessRecord:
    query: str
    business_keyword: str = ""  # solo tipologia business (es. "centro estetico", "idraulico")
    city: str = ""  # solo città (es. "Milano", "Varese")
    name: str = ""
    category: str = ""
    address: str = ""
    phone: str = ""
    website: str = ""
    email: str = ""
    rating: str = ""
    reviews: str = ""
    migliorabile: bool = False
    note: str = ""
    timestamp: str = ""

    def keyword_combo(self) -> str:
        return self.business_keyword or ""

    def to_row(self) -> List[Any]:
        return [
            self.email,
            self.phone,
            self.website,
            self.keyword_combo(),
            "",  # Nome proprietario (non disponibile da Maps)
            self.city,
            "no",  # Inviata - default no per nuovi business
        ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scraper Google Maps -> Google Sheets (gratuito).")
    parser.add_argument("--sheet-id", required=True, help="ID del Google Sheet di destinazione.")
    parser.add_argument("--worksheet", default="Sheet1", help="Nome del foglio (default Sheet1).")
    parser.add_argument("--service-account", help="Percorso al file JSON del service account.")
    parser.add_argument(
        "--service-account-json",
        help="JSON del service account inline (oppure setta env SERVICE_ACCOUNT_JSON).",
    )
    parser.add_argument("--queries-file", help="Percorso a file JSON con lista di query.")
    parser.add_argument("--max-per-query", type=int, default=8, help="Risultati max per query.")
    parser.add_argument("--min-delay", type=float, default=1.0, help="Delay minimo tra card.")
    parser.add_argument("--max-delay", type=float, default=3.5, help="Delay massimo tra card.")
    parser.add_argument("--headful", action="store_true", help="Lancia il browser visibile.")
    return parser.parse_args()


def load_queries(path: Optional[str], fallback_max: int) -> List[Dict[str, Any]]:
    if path:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        items = payload if isinstance(payload, list) else payload.get("queries", [])
    else:
        items = DEFAULT_QUERIES
    parsed: List[Dict[str, Any]] = []
    for item in items:
        keyword = item.get("keyword") or ""
        city = item.get("city") or ""
        if not keyword or not city:
            continue
        parsed.append(
            {
                "keyword": keyword.strip(),
                "city": city.strip(),
                "max": int(item.get("max", fallback_max)),
            }
        )
    return parsed


def build_gspread_client(service_account_path: Optional[str], service_account_json: Optional[str]) -> gspread.Client:
    if service_account_json:
        data = json.loads(service_account_json)
        return gspread.service_account_from_dict(data)
    env_json = os.getenv("SERVICE_ACCOUNT_JSON")
    if env_json:
        data = json.loads(env_json)
        return gspread.service_account_from_dict(data)
    if service_account_path:
        path_obj = Path(service_account_path)
        if path_obj.exists():
            return gspread.service_account(filename=str(path_obj))
    env_path = os.getenv("SERVICE_ACCOUNT_FILE")
    if env_path and Path(env_path).exists():
        return gspread.service_account(filename=env_path)
    raise ValueError("Service account mancante: passa --service-account o --service-account-json o variabile env.")


def get_worksheet(client: gspread.Client, sheet_id: str, worksheet_name: str):
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=7)
    headers = ["Email", "Phone", "Website", "Keyword", "Nome proprietario", "Location", "Inviata"]
    existing = ws.row_values(1)
    if existing != headers:
        ws.update("A1:G1", [headers])
    return ws


def load_existing_websites(ws) -> set:
    try:
        col = ws.col_values(3)  # Website column (1-based index)
    except Exception:
        return set()
    # skip header
    return {w.strip() for w in col[1:] if w and w.strip()}


async def dismiss_consent(page: Page) -> None:
    selectors = [
        "button:has-text('Accetta tutto')",
        "button:has-text('Accetta')",
        "button:has-text('I agree')",
        "button:has-text('Rifiuta tutto')",
        "button:has-text('Rifiuta')",
    ]
    try:
        for sel in selectors:
            btn = page.locator(sel)
            if await btn.count() > 0:
                await btn.click()
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
                await page.wait_for_timeout(500)
                return
    except Exception:
        pass
    # Alcuni consensi stanno in un iframe
    try:
        frame = page.frame_locator("iframe[name*='consent']").first
        for sel in selectors:
            btn = frame.locator(sel)
            if await btn.count() > 0:
                await btn.click()
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
                await page.wait_for_timeout(500)
                return
    except Exception:
        pass
    # Fallback con ruoli accessibili
    try:
        btn = page.get_by_role("button", name=re.compile("Accetta|Agree", re.IGNORECASE))
        if await btn.count() > 0:
            await btn.first.click()
            await page.wait_for_timeout(500)
    except Exception:
        pass


async def go_to_query(page: Page, query: str) -> None:
    url = f"https://www.google.com/maps/search/{quote_plus(query)}?hl=it"
    await page.goto(url, wait_until="domcontentloaded")
    await dismiss_consent(page)
    await page.wait_for_timeout(1000)
    await page.wait_for_selector("div[role='feed']", timeout=20000)


async def ensure_results_loaded(page: Page, target: int) -> None:
    feed = page.locator("div[role='feed']")
    attempts = 0
    while attempts < 12:
        count = await page.locator("div[role='article']").count()
        if count >= target:
            break
        try:
            await feed.evaluate("(el) => el.scrollBy(0, el.scrollHeight)")
        except Exception:
            pass
        await page.wait_for_timeout(random.uniform(600, 1200))
        attempts += 1


async def safe_text(page: Page, selector: str) -> str:
    loc = page.locator(selector).first
    try:
        if await loc.count() == 0:
            return ""
        txt = await loc.inner_text()
        return txt.strip()
    except Exception:
        return ""


async def safe_attr(page: Page, selector: str, attr: str) -> str:
    loc = page.locator(selector).first
    try:
        if await loc.count() == 0:
            return ""
        val = await loc.get_attribute(attr)
        return val or ""
    except Exception:
        return ""


def parse_rating(text: str) -> Tuple[str, str]:
    rating = ""
    reviews = ""
    if text:
        digits = re.findall(r"[\d.,]+", text)
        if digits:
            rating = digits[0].replace(",", ".")
        if len(digits) > 1:
            reviews = digits[1]
    return rating, reviews


def parse_reviews(text: str) -> str:
    if not text:
        return ""
    digits = re.findall(r"\d+", text.replace(".", ""))
    return digits[0] if digits else ""


def extract_city_from_address(address: str) -> str:
    """Estrae la città dall'indirizzo italiano. Formati comuni:
    - Via X, 123, 20100 Milano MI
    - Via X, Milano
    - Piazza X, 20100 Milano MI
    """
    if not address:
        return ""
    # Rimuovi caratteri speciali come \ue0c8 (icona)
    address = re.sub(r"\\u[0-9a-fA-F]{4}", "", address)
    address = address.strip()
    
    # Pattern: CAP (5 cifre) seguito da città e sigla provincia (2 lettere)
    # Es: "20100 Milano MI"
    match = re.search(r"\b\d{5}\s+([A-ZÀ-Ö][a-zà-ö]+(?:\s+[A-ZÀ-Ö][a-zà-ö]+)*)\s+[A-Z]{2}\b", address)
    if match:
        return match.group(1).strip()
    
    # Pattern: città seguita da sigla provincia alla fine
    # Es: "Via X, Milano MI"
    match = re.search(r",\s*([A-ZÀ-Ö][a-zà-ö]+(?:\s+[A-ZÀ-Ö][a-zà-ö]+)*)\s+[A-Z]{2}\s*$", address)
    if match:
        return match.group(1).strip()
    
    # Fallback: ultima parola con iniziale maiuscola (probabilmente la città)
    words = address.split()
    for word in reversed(words):
        if word and word[0].isupper() and len(word) > 2 and not word.endswith(","):
            # Escludi sigle provincia (2 lettere maiuscole) e CAP (5 cifre)
            if len(word) == 2 and word.isupper():
                continue
            if word.isdigit() and len(word) == 5:
                continue
            return word.strip()
    
    return ""


def extract_emails_from_html(html: str) -> List[str]:
    emails = set()
    for match in re.findall(EMAIL_REGEX, html):
        emails.add(unquote(match))
    return sorted(emails)


def choose_best_email(candidates: List[str], website: str) -> str:
    if not candidates:
        return ""
    blacklist_domains = {"wixpress.com", "sentry-next.wixpress.com", "sentry.io"}

    def domain_of(email: str) -> str:
        parts = email.lower().split("@")
        return parts[1] if len(parts) == 2 else ""

    site_domain = urlparse(website).netloc.lower() if website else ""
    filtered: List[str] = []
    for e in candidates:
        if not e:
            continue
        user = e.split("@")[0]
        dom = domain_of(e)
        if not dom:
            continue
        if len(user) > 40:
            continue
        if dom in blacklist_domains or dom.endswith("wixpress.com") or dom.endswith("sentry.io"):
            continue
        if dom.endswith(".js") or ".js" in dom or ".js" in user:
            continue
        filtered.append(e)

    if filtered:
        same_domain = [e for e in filtered if site_domain and domain_of(e) in site_domain]
        if same_domain:
            return same_domain[0]
        common = {
            "gmail.com",
            "outlook.com",
            "hotmail.com",
            "yahoo.it",
            "yahoo.com",
            "virgilio.it",
        }
        common_email = [e for e in filtered if domain_of(e) in common]
        if common_email:
            return common_email[0]
        return filtered[0]
    return ""


def assess_site_quality(html: str, url: str) -> Tuple[bool, str]:
    reasons: List[str] = []
    soup = BeautifulSoup(html, "html.parser")
    
    # Controlli base essenziali
    if not url.startswith("https://"):
        reasons.append("assenza https")
    if not soup.find("meta", attrs={"name": "viewport"}):
        reasons.append("non responsive (viewport mancante)")
    if not soup.find("meta", attrs={"name": "description"}):
        reasons.append("meta description mancante")
    if not soup.find("link", rel=lambda v: v and "icon" in v):
        reasons.append("favicon assente")
    
    # Controlli tecnici datati
    scripts = [s.get("src", "").lower() for s in soup.find_all("script") if s.get("src")]
    for src in scripts:
        if "jquery-1." in src or "jquery1." in src:
            reasons.append("usa jquery 1.x")
            break
        if "bootstrap" in src and ("3." in src or "2." in src):
            reasons.append("bootstrap datato")
            break
    
    # Controlli struttura/layout
    tables = len(soup.find_all("table"))
    divs = len(soup.find_all("div"))
    if tables > 5 and divs < 30:
        reasons.append("layout a tabelle")
    
    # Controlli performance/contenuti
    if len(html) > 400_000:
        reasons.append("pagina pesante >400KB")
    text_content = soup.get_text(" ", strip=True)
    if len(text_content) < 200:
        reasons.append("contenuti scarsi")
    
    # Controlli aggiuntivi per problemi comuni
    title_tag = soup.find("title")
    if not title_tag or not title_tag.get_text(strip=True):
        reasons.append("titolo mancante")
    elif len(title_tag.get_text(strip=True)) < 10:
        reasons.append("titolo troppo corto")
    
    # Controlla se usa servizi gratuiti comuni (spesso segno di siti amatoriali)
    html_str = str(soup).lower()
    if any(service in html_str for service in ["wix.com", "weebly.com", "squarespace.com"]):
        reasons.append("usa servizio gratuito")
    
    # Indici di qualità positiva (siti ben fatti hanno questi)
    has_modern_framework = any(
        "react" in str(s).lower() or "vue" in str(s).lower() or "angular" in str(s).lower() or "next" in str(s).lower()
        for s in soup.find_all("script")
    )
    has_structured_data = bool(soup.find_all(attrs={"itemtype": True}))
    has_og_tags = bool(soup.find("meta", attrs={"property": re.compile("^og:")}))
    has_canonical = bool(soup.find("link", attrs={"rel": "canonical"}))
    has_robots_meta = bool(soup.find("meta", attrs={"name": "robots"}))
    has_schema_org = bool(soup.find_all(attrs={"itemscope": True}))
    
    # Conta caratteristiche positive
    positive_indicators = sum([
        has_modern_framework,
        has_structured_data or has_schema_org,
        has_og_tags,
        has_canonical,
        has_robots_meta,
    ])
    
    # FILTRO RIGIDO: accetta SOLO siti che fanno veramente cagare
    if positive_indicators >= 2:
        # Sito con caratteristiche moderne: SCARTA (troppo ben fatto)
        migliorabile = False
    else:
        # Sito senza caratteristiche moderne: richiedi ALMENO 5 problemi gravi
        migliorabile = len(reasons) >= 5
    
    note = "; ".join(reasons[:4])
    return migliorabile, note


async def fetch_html(client: httpx.AsyncClient, url: str) -> Optional[str]:
    try:
        resp = await client.get(url, timeout=8.0, follow_redirects=True)
        if resp.status_code < 400 and resp.text:
            return resp.text
    except Exception:
        return None
    return None


async def enrich_with_site(
    client: httpx.AsyncClient, website: str
) -> Tuple[str, bool, str]:
    if not website:
        return "", False, ""
    parsed = urlparse(website)
    if not parsed.scheme:
        website = "https://" + website
    candidates = [website]
    base = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else website
    for path in ["/contatti", "/contact", "/about", "/chi-siamo"]:
        candidates.append(urljoin(base, path))
    emails: List[str] = []
    migliorabile = False
    note = ""
    for url in candidates:
        html = await fetch_html(client, url)
        if not html:
            continue
        if not emails:
            emails = extract_emails_from_html(html)
        migliorabile, note = assess_site_quality(html, url)
        if emails and migliorabile:
            break
    email = choose_best_email(emails, website)
    return email, migliorabile, note


async def scrape_card(
    page: Page,
    client: httpx.AsyncClient,
    idx: int,
    query_str: str,
    business_keyword: str,
    city: str,
    delay_range: Tuple[float, float],
) -> Optional[BusinessRecord]:
    cards = page.locator("div[role='article']")
    count = await cards.count()
    if idx >= count:
        return None
    card = cards.nth(idx)
    try:
        await card.scroll_into_view_if_needed()
        await card.click()
    except Exception:
        return None
    await page.wait_for_timeout(random.uniform(600, 1200))
    name = await safe_text(page, "h1.DUwDvf")
    category = await safe_text(page, "button.DkEaL")
    address = await safe_text(page, "button[data-item-id*='address']")
    phone = await safe_text(page, "button[data-item-id*='phone']")
    website = await safe_attr(page, "a[data-item-id*='authority']", "href")
    rating_text = await safe_attr(page, "span[aria-label*='stelle']", "aria-label")
    rating, _ = parse_rating(rating_text)
    reviews_text = await safe_text(page, "button[jsaction*='pane.rating.moreReviews']")
    reviews = parse_reviews(reviews_text)
    email, migliorabile, note = await enrich_with_site(client, website)
    # Estrai la città dall'indirizzo invece di usare quella dalla query
    extracted_city = extract_city_from_address(address)
    actual_city = extracted_city if extracted_city else city  # fallback alla query se non trovata
    ts = datetime.utcnow().isoformat()
    await page.wait_for_timeout(random.uniform(delay_range[0], delay_range[1]) * 1000)
    return BusinessRecord(
        query=query_str,
        business_keyword=business_keyword,
        city=actual_city,
        name=name,
        category=category,
        address=address,
        phone=phone,
        website=website,
        email=email,
        rating=rating,
        reviews=reviews,
        migliorabile=migliorabile,
        note=note,
        timestamp=ts,
    )


async def scrape_query(
    page: Page,
    client: httpx.AsyncClient,
    query: Dict[str, Any],
    max_per_query: int,
    delay_range: Tuple[float, float],
) -> List[BusinessRecord]:
    business_keyword = query.get("keyword", "").strip()
    city = query.get("city", "").strip()
    term = f"{business_keyword} {city}"
    await go_to_query(page, term)
    target = min(query.get("max", max_per_query), max_per_query)
    await ensure_results_loaded(page, target)
    records: List[BusinessRecord] = []
    for idx in range(target):
        rec = await scrape_card(page, client, idx, term, business_keyword, city, delay_range)
        if rec:
            records.append(rec)
    return records


def write_rows(ws, records: Sequence[BusinessRecord]) -> None:
    rows = [r.to_row() for r in records]
    if not rows:
        return
    
    # Retry con backoff esponenziale per errori di connessione
    max_retries = 5
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            ws.append_rows(rows, value_input_option="USER_ENTERED")
            return
        except (ConnectionError, Exception) as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Errore connessione Google Sheets (tentativo {attempt + 1}/{max_retries}), riprovo tra {delay:.1f}s...")
                time.sleep(delay)
            else:
                print(f"Errore dopo {max_retries} tentativi: {e}")
                raise


def dedup_records(records: Sequence[BusinessRecord], existing_websites: set) -> List[BusinessRecord]:
    seen = set(existing_websites)
    unique: List[BusinessRecord] = []
    for r in records:
        website = (r.website or "").strip()
        if website:
            if website in seen:
                continue
            seen.add(website)
        unique.append(r)
    return unique


def filter_with_email(records: Sequence[BusinessRecord]) -> List[BusinessRecord]:
    return [r for r in records if (r.email or "").strip()]


def filter_only_bad_sites(records: Sequence[BusinessRecord]) -> List[BusinessRecord]:
    """Filtra SOLO i business con siti che fanno veramente cagare (migliorabile=True)."""
    return [r for r in records if r.migliorabile]


async def run() -> None:
    args = parse_args()
    queries = load_queries(args.queries_file, args.max_per_query)
    if args.min_delay > args.max_delay:
        raise ValueError("min-delay deve essere <= max-delay")
    client = build_gspread_client(args.service_account, args.service_account_json)
    ws = get_worksheet(client, args.sheet_id, args.worksheet)
    existing_websites = load_existing_websites(ws)
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(
            headless=not args.headful,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await browser.new_page(user_agent=HEADERS["User-Agent"], viewport={"width": 1300, "height": 900})
        async with httpx.AsyncClient(headers=HEADERS) as http_client:
            all_records: List[BusinessRecord] = []
            for item in queries:
                recs = await scrape_query(
                    page,
                    http_client,
                    item,
                    max_per_query=args.max_per_query,
                    delay_range=(args.min_delay, args.max_delay),
                )
                all_records.extend(recs)
                await page.wait_for_timeout(random.uniform(8000, 12000))
            if all_records:
                # Filtro 1: solo quelli con email
                with_email = filter_with_email(all_records)
                # Filtro 2: solo quelli con siti che fanno veramente cagare
                bad_sites = filter_only_bad_sites(with_email)
                # Dedup
                unique_records = dedup_records(bad_sites, existing_websites)
                write_rows(ws, unique_records)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())

