# Luma Outreach OS

Autonomous AI-powered LinkedIn and email outreach system. Researches prospects, generates content via Claude, executes outreach via Playwright and Gmail API, and logs everything to Google Sheets.

## Architecture

```
run_scheduler.py (orchestrator)
  ├── sheet_client.py    → Read prospects/targets/inbound, write activities
  ├── brave_search.py    → Live web research via SerpAPI (Google Search)
  ├── claude_client.py   → AI content generation via Claude CLI
  ├── linkedin_automation.py → Playwright: posts, comments, DMs, connections
  └── gmail_sender.py    → Gmail API: send outreach emails
```

## Schedule

Runs automatically via GitHub Actions at:
- **12:00 IST** (06:30 UTC)
- **19:00 IST** (13:30 UTC)

## Daily Caps

| Action              | Max per run |
|---------------------|-------------|
| LinkedIn Posts      | 2           |
| LinkedIn Comments   | 10          |
| Connection Requests | 25          |
| Emails              | 20          |

## Setup

### 1. Google Sheets

Create a Google Sheet with four tabs:

**Prospects** — columns:
`name | company | title | linkedin_url | email | status | notes`

**Targets** — columns:
`post_url | topic | priority | status`

**Inbound** — columns:
`sender_name | sender_url | message_text | received_at | status`

**Activities** — columns:
`timestamp_utc | channel | activity_type | prospect_name | status | sent_at | draft_text | evidence_snippets`

### 2. Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project, enable **Google Sheets API** and **Gmail API**.
3. Create a **Service Account**, download the JSON key.
4. Share the Google Sheet with the service account email.
5. For Gmail, set up **OAuth 2.0** credentials and generate a `gmail_token.json` via the OAuth consent flow.

### 3. LinkedIn Session

LinkedIn uses 2FA, so we persist session cookies:

1. Log in to LinkedIn in a Chromium browser.
2. Export cookies to a JSON file (use a browser extension or DevTools).
3. Save as `session.json` with this structure:

```json
[
  {"name": "li_at", "value": "YOUR_LI_AT_COOKIE", "domain": ".linkedin.com", "path": "/"},
  {"name": "JSESSIONID", "value": "YOUR_JSESSIONID", "domain": ".linkedin.com", "path": "/"}
]
```

4. Base64-encode and store as a GitHub Secret: `LINKEDIN_SESSION_B64`.

**Refresh cadence:** Re-export cookies every 7-14 days before they expire.

### 4. Environment Variables / GitHub Secrets

| Secret                      | Description                              |
|-----------------------------|------------------------------------------|
| `GOOGLE_CREDENTIALS_B64`    | Base64-encoded service account JSON      |
| `GMAIL_TOKEN_B64`           | Base64-encoded Gmail OAuth token JSON    |
| `GOOGLE_SHEET_ID`           | The Google Sheet document ID             |
| `LINKEDIN_SESSION_B64`      | Base64-encoded LinkedIn session cookies  |
| `SERPAPI_KEY`               | SerpAPI key (free: 100 searches/month)   |
| `GMAIL_SENDER_EMAIL`        | The Gmail address to send from           |

### 5. Local Development

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install chromium

# Set environment variables
export GOOGLE_SHEET_ID="your-sheet-id"
export SERPAPI_KEY="your-serpapi-key"
export GMAIL_SENDER_EMAIL="you@gmail.com"

# Place credential files in project root:
# - google_credentials.json
# - gmail_token.json
# - session.json

python scripts/run_scheduler.py
```

## Prompt Engineering

All prompts live in `prompts/`. Edit `rules.md` to change tone, style constraints, and evidence requirements. Each prompt file is loaded at runtime and injected into Claude calls.

## Safety

- Random sleep (5-15s) between LinkedIn actions to mimic human behavior.
- Daily caps enforced in the orchestrator.
- Confidence score threshold (0.7) — low-confidence drafts are logged as SKIPPED.
- All actions logged to the Activities tab for full auditability.
