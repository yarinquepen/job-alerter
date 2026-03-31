# Yarin's Job Alerter 🔔
Scrapes LinkedIn, Glassdoor & Secret Tel Aviv every 6 hours and sends new finance/treasury job listings directly to your WhatsApp.

---

## How it works
1. Every 6 hours the script scrapes job listings for your 4 target roles across Israel
2. It compares against a local database of jobs already seen
3. Any new jobs trigger an instant WhatsApp message via CallMeBot (free)

---

## Setup — Step by step

### Step 1 — Activate CallMeBot (WhatsApp API)
1. Open WhatsApp and send this message to **+34 644 59 21 28**:
   ```
   I allow callmebot to send me messages
   ```
2. Wait for a reply — it will contain your **API key** (e.g. `1234567`)
3. Save that API key — you will need it in Step 3

### Step 2 — Upload code to GitHub
1. Create a free account at [github.com](https://github.com)
2. Create a new repository called `job-alerter`
3. Upload all 4 files from this folder:
   - `main.py`
   - `requirements.txt`
   - `render.yaml`
   - `README.md`

### Step 3 — Deploy to Render (free server)
1. Create a free account at [render.com](https://render.com)
2. Click **New → Blueprint** and connect your GitHub repo
3. Render will detect `render.yaml` automatically
4. Set the two environment variables when prompted:
   - `WHATSAPP_PHONE` → your number in international format, e.g. `+972501234567`
   - `CALLMEBOT_APIKEY` → the API key you got in Step 1
5. Click **Apply** — the server starts immediately

### Step 4 — Verify it works
- Check the Render logs — you should see `Job alerter starting` and the first scan results
- Within a few minutes you should receive your first WhatsApp message with current job listings

---

## Customisation

### Change how often it checks
In `render.yaml`, change the value of `CHECK_INTERVAL_H`:
- `"3"` → every 3 hours
- `"6"` → every 6 hours (default)
- `"12"` → twice a day

### Add or remove job search queries
In `main.py`, edit the `SEARCH_QUERIES` list:
```python
SEARCH_QUERIES = [
    "Treasury Analyst Israel",
    "Finance Operations Analyst Tel Aviv",
    "FP&A Analyst Israel",
    "Financial Analyst Tel Aviv",
    "Payments Analyst Israel",      # add any role you want
]
```

### Add more companies to watch
The scraper already picks up all companies from LinkedIn and Glassdoor.
If you want to add a specific company's careers page, add a new scraper
function in `main.py` following the same pattern as `scrape_secrettelaviv()`.

---

## Cost
- **Render free tier**: 750 hours/month — enough to run 24/7 at no cost
- **CallMeBot**: completely free
- **Total monthly cost: $0**

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No WhatsApp received | Make sure you sent the activation message to CallMeBot first |
| Wrong phone format | Use `+972XXXXXXXXX` format, no spaces or dashes |
| Render shows errors | Check logs — missing env variables are the most common cause |
| No jobs found | LinkedIn/Glassdoor sometimes block scrapers — the script will retry next cycle |
