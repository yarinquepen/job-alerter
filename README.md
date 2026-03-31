# Yarin's Job Alerter 🔔
Scrapes LinkedIn, Glassdoor, Secret Tel Aviv & 25 company career pages every 6 hours.
Sends new finance/treasury job listings directly to your Telegram.

---

## What it monitors
**Job roles:** Treasury Analyst · Finance Operations · FP&A · Financial Analyst · Payments Analyst · Finance Manager

**Sources:**
- LinkedIn (6 search queries)
- Glassdoor (6 search queries)
- Secret Tel Aviv Jobs
- 25 company career pages directly: monday.com, Wix, eToro, Tipalti, Payoneer, Fiverr, Taboola, Lightricks, CyberArk, Check Point, WalkMe, Gong, Lemonade, Playtika, ironSource, Varonis, NICE, Amdocs, AppsFlyer, Similarweb, Papaya Global, Nuvei, Outbrain, Kaltura, Perion

---

## Setup — 3 steps

### Step 1 — Create your Telegram bot (3 min)
1. Open Telegram and search for **@BotFather**
2. Send: `/newbot`
3. Follow the prompts — choose any name and username for the bot
4. BotFather replies with your **bot token** — looks like: `7123456789:AAFxxxxxxxxxxxxxx`
5. Save this token

**Get your Chat ID:**
1. Search for **@userinfobot** on Telegram
2. Start it — it instantly replies with your **Chat ID** (a number like `123456789`)
3. Save this number

### Step 2 — Upload to GitHub
1. Create a free account at github.com
2. Create a new repository called `job-alerter` (set to Public, add a README)
3. Delete the auto-generated README.md
4. Upload these 4 files: `main.py`, `requirements.txt`, `render.yaml`, `README.md`

### Step 3 — Deploy on Render (free server)
1. Create a free account at render.com
2. Click **New → Blueprint** and connect your GitHub repo
3. Render detects `render.yaml` automatically
4. Fill in the environment variables:
   - `TELEGRAM_TOKEN` → your bot token from Step 1
   - `TELEGRAM_CHAT_ID` → your chat ID from Step 1
5. Click **Apply** — the server starts immediately

**First message arrives within ~2 minutes of deploying.**

---

## What a Telegram message looks like
```
New job alerts for Yarin 🔔

1. Treasury Analyst
🏢 monday.com   📍 Tel Aviv
🔗 https://monday.com/careers/job/123
via LinkedIn

2. FP&A Analyst
🏢 Wix   📍 Tel Aviv
🔗 https://wix.com/jobs/456
via Glassdoor
```

---

## Customisation

### Change check frequency
In `render.yaml`, change `CHECK_INTERVAL_H`:
- `"3"` — every 3 hours
- `"6"` — every 6 hours (default)
- `"12"` — twice a day

### Add more job roles to track
In `main.py`, add keywords to `ROLE_KEYWORDS`:
```python
ROLE_KEYWORDS = [
    "treasury",
    "your new keyword here",   # add any role
    ...
]
```

### Add more companies
In `main.py`, add to the `COMPANIES` list:
```python
{"name": "Company Name", "careers_url": "https://company.com/careers"},
```

---

## Cost
- Render free tier: 750 hours/month — enough for 24/7 at zero cost
- Telegram bot API: completely free, no limits
- **Total: $0/month**

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No Telegram message received | Make sure you started a chat with your bot first (send it `/start`) |
| "Unauthorized" error in logs | TELEGRAM_TOKEN is wrong — double check it in Render env vars |
| "Chat not found" error | TELEGRAM_CHAT_ID is wrong — get it again from @userinfobot |
| No jobs found | LinkedIn/Glassdoor occasionally block scrapers — script retries next cycle |
| Render deploy fails | Check that all 4 files are uploaded to GitHub correctly |
