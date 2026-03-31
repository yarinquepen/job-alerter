import os
import time
import sqlite3
import hashlib
import requests
import logging
from datetime import datetime
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
WHATSAPP_PHONE   = os.environ["WHATSAPP_PHONE"]    # e.g. +972501234567
CALLMEBOT_APIKEY = os.environ["CALLMEBOT_APIKEY"]  # from callmebot.com
CHECK_INTERVAL_H = int(os.getenv("CHECK_INTERVAL_H", "6"))
DB_PATH          = os.getenv("DB_PATH", "seen_jobs.db")

# ── Job search config ──────────────────────────────────────────────────────────
SEARCH_QUERIES = [
    "Treasury Analyst Israel",
    "Finance Operations Analyst Tel Aviv",
    "FP&A Analyst Israel",
    "Financial Analyst Tel Aviv",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Database ───────────────────────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS seen_jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT,
            source TEXT,
            found_at TEXT
        )
    """)
    con.commit()
    return con


def is_seen(con, job_id: str) -> bool:
    row = con.execute("SELECT 1 FROM seen_jobs WHERE id=?", (job_id,)).fetchone()
    return row is not None


def mark_seen(con, job: dict):
    con.execute(
        "INSERT OR IGNORE INTO seen_jobs VALUES (?,?,?,?,?,?,?)",
        (
            job["id"], job["title"], job["company"],
            job["location"], job["url"], job["source"],
            datetime.utcnow().isoformat(),
        ),
    )
    con.commit()


# ── Scrapers ───────────────────────────────────────────────────────────────────
def job_id(title: str, company: str, url: str) -> str:
    raw = f"{title.lower().strip()}{company.lower().strip()}{url}"
    return hashlib.md5(raw.encode()).hexdigest()


def scrape_linkedin(query: str) -> list[dict]:
    jobs = []
    encoded = query.replace(" ", "%20")
    url = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={encoded}&location=Israel&f_TPR=r86400&f_E=2%2C3"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("div.base-card")[:10]
        for card in cards:
            title_el   = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle")
            loc_el     = card.select_one("span.job-search-card__location")
            link_el    = card.select_one("a.base-card__full-link")
            if not (title_el and company_el and link_el):
                continue
            title   = title_el.get_text(strip=True)
            company = company_el.get_text(strip=True)
            loc     = loc_el.get_text(strip=True) if loc_el else "Israel"
            href    = link_el["href"].split("?")[0]
            jobs.append({
                "id":       job_id(title, company, href),
                "title":    title,
                "company":  company,
                "location": loc,
                "url":      href,
                "source":   "LinkedIn",
            })
        log.info(f"LinkedIn [{query}]: {len(jobs)} jobs found")
    except Exception as e:
        log.warning(f"LinkedIn scrape failed for '{query}': {e}")
    return jobs


def scrape_glassdoor(query: str) -> list[dict]:
    jobs = []
    encoded = query.replace(" ", "-").lower()
    url = f"https://www.glassdoor.com/Job/israel-{encoded}-jobs-SRCH_IL.0,6_IN119_KO7,{7+len(encoded)}.htm"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("li.react-job-listing")[:10]
        for card in cards:
            title_el   = card.select_one("[data-test='job-title']")
            company_el = card.select_one("[data-test='employer-name']")
            loc_el     = card.select_one("[data-test='emp-location']")
            link_el    = card.select_one("a[data-test='job-title']")
            if not (title_el and company_el and link_el):
                continue
            title   = title_el.get_text(strip=True)
            company = company_el.get_text(strip=True)
            loc     = loc_el.get_text(strip=True) if loc_el else "Israel"
            href    = "https://www.glassdoor.com" + link_el.get("href", "")
            jobs.append({
                "id":       job_id(title, company, href),
                "title":    title,
                "company":  company,
                "location": loc,
                "url":      href,
                "source":   "Glassdoor",
            })
        log.info(f"Glassdoor [{query}]: {len(jobs)} jobs found")
    except Exception as e:
        log.warning(f"Glassdoor scrape failed for '{query}': {e}")
    return jobs


def scrape_secrettelaviv() -> list[dict]:
    jobs = []
    url = "https://jobs.secrettelaviv.com/list/category/financial-analyst/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("article.job_listing")[:15]
        for card in cards:
            title_el   = card.select_one("h3")
            company_el = card.select_one(".company")
            loc_el     = card.select_one(".location")
            link_el    = card.select_one("a")
            if not (title_el and link_el):
                continue
            title   = title_el.get_text(strip=True)
            company = company_el.get_text(strip=True) if company_el else "Unknown"
            loc     = loc_el.get_text(strip=True) if loc_el else "Tel Aviv"
            href    = link_el["href"]
            jobs.append({
                "id":       job_id(title, company, href),
                "title":    title,
                "company":  company,
                "location": loc,
                "url":      href,
                "source":   "Secret Tel Aviv",
            })
        log.info(f"Secret Tel Aviv: {len(jobs)} jobs found")
    except Exception as e:
        log.warning(f"Secret Tel Aviv scrape failed: {e}")
    return jobs


# ── WhatsApp sender ────────────────────────────────────────────────────────────
def send_whatsapp(jobs: list[dict]):
    if not jobs:
        return
    lines = ["*New job alerts for Yarin* 🔔\n"]
    for i, j in enumerate(jobs, 1):
        lines.append(
            f"*{i}. {j['title']}*\n"
            f"🏢 {j['company']}  📍 {j['location']}\n"
            f"🔗 {j['url']}\n"
            f"_(via {j['source']})_\n"
        )
    message = "\n".join(lines)
    encoded = requests.utils.quote(message)
    api_url = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={WHATSAPP_PHONE}&text={encoded}&apikey={CALLMEBOT_APIKEY}"
    )
    try:
        r = requests.get(api_url, timeout=15)
        if r.ok:
            log.info(f"WhatsApp sent — {len(jobs)} new job(s)")
        else:
            log.warning(f"WhatsApp API error: {r.status_code} {r.text[:200]}")
    except Exception as e:
        log.error(f"WhatsApp send failed: {e}")


# ── Main check cycle ───────────────────────────────────────────────────────────
def check_jobs():
    log.info("=== Starting job check ===")
    con = init_db()

    all_jobs: list[dict] = []

    # Scrape LinkedIn and Glassdoor for each query
    for query in SEARCH_QUERIES:
        all_jobs.extend(scrape_linkedin(query))
        time.sleep(2)
        all_jobs.extend(scrape_glassdoor(query))
        time.sleep(2)

    # Scrape Secret Tel Aviv (single pass covers all finance roles)
    all_jobs.extend(scrape_secrettelaviv())

    # Deduplicate within this batch by id
    seen_ids = set()
    unique_jobs = []
    for j in all_jobs:
        if j["id"] not in seen_ids:
            seen_ids.add(j["id"])
            unique_jobs.append(j)

    # Filter to only genuinely new jobs
    new_jobs = [j for j in unique_jobs if not is_seen(con, j["id"])]
    log.info(f"Total scraped: {len(unique_jobs)} | New: {len(new_jobs)}")

    if new_jobs:
        # Send WhatsApp in batches of 5 to keep messages readable
        batch_size = 5
        for i in range(0, len(new_jobs), batch_size):
            batch = new_jobs[i : i + batch_size]
            send_whatsapp(batch)
            time.sleep(3)
        # Mark all new jobs as seen
        for j in new_jobs:
            mark_seen(con, j)
    else:
        log.info("No new jobs found — nothing sent")

    con.close()
    log.info("=== Check complete ===\n")


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info(f"Job alerter starting — checking every {CHECK_INTERVAL_H}h")
    log.info(f"Sending alerts to WhatsApp: {WHATSAPP_PHONE}")

    # Run once immediately on startup
    check_jobs()

    # Then schedule recurring checks
    scheduler = BlockingScheduler()
    scheduler.add_job(check_jobs, "interval", hours=CHECK_INTERVAL_H)
    log.info(f"Scheduler running — next check in {CHECK_INTERVAL_H}h")
    scheduler.start()
