import os
import time
import sqlite3
import hashlib
import requests
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config (set these as environment variables on Render) ──────────────────────
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]    # from @BotFather
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]  # your personal chat ID
CHECK_INTERVAL_H = int(os.getenv("CHECK_INTERVAL_H", "6"))
DB_PATH          = os.getenv("DB_PATH", "seen_jobs.db")

# ── Role keywords to filter relevant jobs ─────────────────────────────────────
ROLE_KEYWORDS = [
    "treasury", "finance operations", "fp&a", "financial analyst",
    "financial planning", "payments analyst", "cash management",
    "finance manager", "controller", "accounts payable", "accounts receivable",
]

# ── LinkedIn & Glassdoor search queries ───────────────────────────────────────
SEARCH_QUERIES = [
    "Treasury Analyst Israel",
    "Finance Operations Analyst Tel Aviv",
    "FP&A Analyst Israel",
    "Financial Analyst Tel Aviv",
    "Payments Analyst Israel",
    "Finance Manager Tel Aviv",
]

# ── 25 Tel Aviv high-tech companies ───────────────────────────────────────────
COMPANIES = [
    {"name": "monday.com",    "careers_url": "https://monday.com/careers"},
    {"name": "Wix",           "careers_url": "https://www.wix.com/jobs"},
    {"name": "eToro",         "careers_url": "https://www.etoro.com/careers/"},
    {"name": "Tipalti",       "careers_url": "https://tipalti.com/careers/"},
    {"name": "Payoneer",      "careers_url": "https://www.payoneer.com/careers/"},
    {"name": "Fiverr",        "careers_url": "https://www.fiverr.com/careers"},
    {"name": "Taboola",       "careers_url": "https://www.taboola.com/careers"},
    {"name": "Lightricks",    "careers_url": "https://www.lightricks.com/careers"},
    {"name": "CyberArk",      "careers_url": "https://www.cyberark.com/careers/"},
    {"name": "Check Point",   "careers_url": "https://www.checkpoint.com/careers/"},
    {"name": "WalkMe",        "careers_url": "https://www.walkme.com/careers/"},
    {"name": "Gong",          "careers_url": "https://www.gong.io/careers/"},
    {"name": "Lemonade",      "careers_url": "https://makers.lemonade.com/"},
    {"name": "Playtika",      "careers_url": "https://www.playtika.com/careers/"},
    {"name": "ironSource",    "careers_url": "https://www.is.com/careers/"},
    {"name": "Varonis",       "careers_url": "https://www.varonis.com/careers"},
    {"name": "NICE",          "careers_url": "https://www.nice.com/about/careers"},
    {"name": "Amdocs",        "careers_url": "https://www.amdocs.com/about/careers"},
    {"name": "AppsFlyer",     "careers_url": "https://www.appsflyer.com/careers/"},
    {"name": "Similarweb",    "careers_url": "https://www.similarweb.com/corp/careers/"},
    {"name": "Papaya Global", "careers_url": "https://www.papayaglobal.com/careers/"},
    {"name": "Nuvei",         "careers_url": "https://www.nuvei.com/careers"},
    {"name": "Outbrain",      "careers_url": "https://www.outbrain.com/careers/"},
    {"name": "Kaltura",       "careers_url": "https://corp.kaltura.com/company/careers/"},
    {"name": "Perion",        "careers_url": "https://www.perion.com/careers/"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def job_id(title: str, company: str, url: str) -> str:
    raw = f"{title.lower().strip()}{company.lower().strip()}{url}"
    return hashlib.md5(raw.encode()).hexdigest()


def is_relevant(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in ROLE_KEYWORDS)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Database ───────────────────────────────────────────────────────────────────
def init_db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS seen_jobs (
            id       TEXT PRIMARY KEY,
            title    TEXT,
            company  TEXT,
            location TEXT,
            url      TEXT,
            source   TEXT,
            found_at TEXT
        )
    """)
    con.commit()
    return con


def is_seen(con: sqlite3.Connection, jid: str) -> bool:
    return con.execute(
        "SELECT 1 FROM seen_jobs WHERE id=?", (jid,)
    ).fetchone() is not None


def mark_seen(con: sqlite3.Connection, job: dict):
    con.execute(
        "INSERT OR IGNORE INTO seen_jobs VALUES (?,?,?,?,?,?,?)",
        (job["id"], job["title"], job["company"],
         job["location"], job["url"], job["source"], now_utc()),
    )
    con.commit()


# ── Scrapers ───────────────────────────────────────────────────────────────────
def scrape_linkedin(query: str) -> list:
    jobs = []
    encoded = query.replace(" ", "%20")
    url = (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={encoded}&location=Israel&f_TPR=r86400&f_E=2%2C3"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select("div.base-card")[:15]:
            title_el   = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle")
            loc_el     = card.select_one("span.job-search-card__location")
            link_el    = card.select_one("a.base-card__full-link")
            if not (title_el and company_el and link_el):
                continue
            title   = title_el.get_text(strip=True)
            company = company_el.get_text(strip=True)
            if not is_relevant(title):
                continue
            loc  = loc_el.get_text(strip=True) if loc_el else "Israel"
            href = link_el["href"].split("?")[0]
            jobs.append({"id": job_id(title, company, href), "title": title,
                         "company": company, "location": loc,
                         "url": href, "source": "LinkedIn"})
        log.info(f"LinkedIn [{query}]: {len(jobs)} relevant jobs")
    except Exception as e:
        log.warning(f"LinkedIn failed for '{query}': {e}")
    return jobs


def scrape_glassdoor(query: str) -> list:
    jobs = []
    slug = query.replace(" ", "-").lower()
    url  = (
        f"https://www.glassdoor.com/Job/israel-{slug}-jobs"
        f"-SRCH_IL.0,6_IN119_KO7,{7+len(slug)}.htm"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select("li.react-job-listing")[:15]:
            title_el   = card.select_one("[data-test='job-title']")
            company_el = card.select_one("[data-test='employer-name']")
            loc_el     = card.select_one("[data-test='emp-location']")
            link_el    = card.select_one("a[data-test='job-title']")
            if not (title_el and company_el and link_el):
                continue
            title   = title_el.get_text(strip=True)
            company = company_el.get_text(strip=True)
            if not is_relevant(title):
                continue
            loc  = loc_el.get_text(strip=True) if loc_el else "Israel"
            href = "https://www.glassdoor.com" + link_el.get("href", "")
            jobs.append({"id": job_id(title, company, href), "title": title,
                         "company": company, "location": loc,
                         "url": href, "source": "Glassdoor"})
        log.info(f"Glassdoor [{query}]: {len(jobs)} relevant jobs")
    except Exception as e:
        log.warning(f"Glassdoor failed for '{query}': {e}")
    return jobs


def scrape_secrettelaviv() -> list:
    jobs = []
    url = "https://jobs.secrettelaviv.com/list/category/financial-analyst/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select("article.job_listing")[:20]:
            title_el   = card.select_one("h3")
            company_el = card.select_one(".company")
            loc_el     = card.select_one(".location")
            link_el    = card.select_one("a")
            if not (title_el and link_el):
                continue
            title   = title_el.get_text(strip=True)
            company = company_el.get_text(strip=True) if company_el else "Unknown"
            if not is_relevant(title):
                continue
            loc  = loc_el.get_text(strip=True) if loc_el else "Tel Aviv"
            href = link_el["href"]
            jobs.append({"id": job_id(title, company, href), "title": title,
                         "company": company, "location": loc,
                         "url": href, "source": "Secret Tel Aviv"})
        log.info(f"Secret Tel Aviv: {len(jobs)} relevant jobs")
    except Exception as e:
        log.warning(f"Secret Tel Aviv failed: {e}")
    return jobs


def scrape_company_page(company: dict) -> list:
    jobs = []
    try:
        r = requests.get(company["careers_url"], headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for link in soup.select("a"):
            title = link.get_text(strip=True)
            if not title or len(title) < 5 or len(title) > 120:
                continue
            if not is_relevant(title):
                continue
            href = link.get("href", "")
            if not href:
                continue
            if href.startswith("/"):
                base = "/".join(company["careers_url"].split("/")[:3])
                href = base + href
            elif not href.startswith("http"):
                continue
            jobs.append({"id": job_id(title, company["name"], href),
                         "title": title, "company": company["name"],
                         "location": "Tel Aviv area", "url": href,
                         "source": "Company page"})
        if jobs:
            log.info(f"{company['name']}: {len(jobs)} relevant jobs")
    except Exception as e:
        log.warning(f"{company['name']} failed: {e}")
    return jobs


# ── Telegram ───────────────────────────────────────────────────────────────────
def escape_md(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2."""
    for ch in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


def build_message(jobs: list) -> str:
    lines = ["*New job alerts for Yarin* 🔔\n"]
    for i, j in enumerate(jobs, 1):
        lines.append(
            f"*{i}\\. {escape_md(j['title'])}*\n"
            f"🏢 {escape_md(j['company'])}   📍 {escape_md(j['location'])}\n"
            f"🔗 {j['url']}\n"
            f"_via {escape_md(j['source'])}_\n"
        )
    return "\n".join(lines)


def send_telegram(jobs: list):
    if not jobs:
        return
    for i in range(0, len(jobs), 5):
        batch   = jobs[i : i + 5]
        message = build_message(batch)
        url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id":                  TELEGRAM_CHAT_ID,
            "text":                     message,
            "parse_mode":               "MarkdownV2",
            "disable_web_page_preview": True,
        }
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.ok:
                log.info(f"Telegram sent {len(batch)} job(s)")
            else:
                log.warning(f"Telegram error: {r.status_code} — {r.text[:200]}")
        except Exception as e:
            log.error(f"Telegram send failed: {e}")
        time.sleep(1)


# ── Main cycle ─────────────────────────────────────────────────────────────────
def check_jobs():
    log.info("=" * 50)
    log.info("Starting job check")
    log.info("=" * 50)
    con      = init_db()
    all_jobs = []

    for query in SEARCH_QUERIES:
        all_jobs.extend(scrape_linkedin(query))
        time.sleep(2)
        all_jobs.extend(scrape_glassdoor(query))
        time.sleep(2)

    all_jobs.extend(scrape_secrettelaviv())
    time.sleep(2)

    for company in COMPANIES:
        all_jobs.extend(scrape_company_page(company))
        time.sleep(1)

    # Deduplicate within batch
    seen_ids: set = set()
    unique_jobs   = []
    for j in all_jobs:
        if j["id"] not in seen_ids:
            seen_ids.add(j["id"])
            unique_jobs.append(j)

    new_jobs = [j for j in unique_jobs if not is_seen(con, j["id"])]
    log.info(f"Scraped: {len(all_jobs)} | Unique: {len(unique_jobs)} | New: {len(new_jobs)}")

    if new_jobs:
        send_telegram(new_jobs)
        for j in new_jobs:
            mark_seen(con, j)
        log.info(f"Marked {len(new_jobs)} jobs as seen")
    else:
        log.info("No new jobs — nothing sent")

    con.close()
    log.info("Job check complete\n")


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info(f"Job alerter starting — Telegram | every {CHECK_INTERVAL_H}h | {len(COMPANIES)} companies")
    check_jobs()
    scheduler = BlockingScheduler()
    scheduler.add_job(check_jobs, "interval", hours=CHECK_INTERVAL_H)
    log.info(f"Scheduler running — next check in {CHECK_INTERVAL_H}h")
    scheduler.start()
