# Stock Analysis Pipeline

Automated weekly pipeline that runs parallel subagents per company in a watchlist, evaluates each against a dividend/value framework, and writes results to a Google Sheet ranked by opportunity.

> Every Monday night the pipeline runs automatically via GitHub Actions. Tuesday morning the analysis is ready in the sheet.

---

## How it works

```
orchestrator.py
├── GitHub Actions scheduler (Monday 23:00 UTC)
├── subagent per ticker — runs in parallel
│   ├── fetch: yfinance (free, no API key needed)
│   ├── calculate: spread vs analyst consensus target
│   └── score: DY, DGR, Payout Ratio, FCF coverage, Spread
└── write → Google Sheets (one row per ticker, date column for history)
```

Each ticker is scored 0–5. One point per metric that passes its threshold.

| Metric | Threshold | Description |
|--------|-----------|-------------|
| DY | ≥ 2.5% | Dividend Yield |
| DGR | ≥ 5.0% | 5-year Dividend Growth Rate (CAGR) |
| Payout Ratio | ≤ 75% | Dividends / Earnings |
| FCF Coverage | ≥ 1.2x | Free Cash Flow / Dividends Paid |
| Spread | ≥ 10% | (Analyst target − Price) / Price |

---

## Output

Results are written to a single Google Sheet tab (`Analysis`). Each weekly run appends 8 rows — one per ticker — with the run date in column A. Re-running the same day overwrites that day's rows instead of duplicating.

**Columns:** Date · Rank · Ticker · Name · Sector · Score · DY% · DGR% · Payout% · FCFcov · Spread% · Price · Target · DPS/yr · ✓/✗ per criterion

---

## Project structure

```
├── orchestrator.py          # entry point: scheduler + parallel launcher + consolidator
├── subagent.py              # single-ticker analysis logic
├── sources/
│   ├── yfinance_source.py   # live data via yfinance (free, no key)
│   ├── mock.py              # offline test data for all watchlist tickers
│   ├── sp_global.py         # S&P Global stub (paid, unused by default)
│   └── daloopa.py           # Daloopa stub (paid, unused by default)
├── output/
│   ├── gsheets.py           # Google Sheets writer
│   └── gdoc.py              # plain-text renderer (used by --dry-run)
├── .github/workflows/
│   └── pipeline.yml         # GitHub Actions: cron + manual trigger
├── watchlist.json           # tickers to analyze
├── config.py                # thresholds and env var references
└── requirements.txt
```

---

## Watchlist

Edit `watchlist.json` to add or remove tickers:

```json
[
  { "ticker": "JNJ",  "name": "Johnson & Johnson", "sector": "Healthcare" },
  { "ticker": "KO",   "name": "Coca-Cola",          "sector": "Consumer Staples" }
]
```

---

## Setup

### 1. Google Sheets

1. Create a blank Google Sheet and rename the first tab to `Analysis`
2. Go to [Google Cloud Console](https://console.cloud.google.com) → create a project → enable **Google Sheets API**
3. Create a **Service Account** → download the JSON key
4. Share the sheet with the service account email (Editor role)

### 2. GitHub Actions secrets

Add these four secrets in **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `GOOGLE_CLIENT_EMAIL` | Service account email (`...@....iam.gserviceaccount.com`) |
| `GOOGLE_SPREADSHEET_ID` | ID from the sheet URL |
| `GOOGLE_PRIVATE_KEY_P1` | First half of base64-encoded private key |
| `GOOGLE_PRIVATE_KEY_P2` | Second half of base64-encoded private key |

To generate `PRIVATE_KEY_P1` and `P2` from your downloaded JSON file:

```bash
python3 -c "
import json, base64
with open('service-account.json') as f:
    d = json.load(f)
b64 = base64.b64encode(d['private_key'].encode()).decode()
mid = len(b64) // 2
print('P1:', b64[:mid])
print('P2:', b64[mid:])
"
```

### 3. Trigger

The pipeline runs automatically every **Monday at 23:00 UTC**.

To trigger manually: **Actions → Stock Analysis Pipeline → Run workflow**.

---

## Local usage

```bash
pip install -r requirements.txt

# Test with no credentials
python orchestrator.py --mock --dry-run

# Live data, print to stdout
python orchestrator.py --yfinance --dry-run

# Live data → write to Google Sheets
export GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/sa.json
export GOOGLE_SPREADSHEET_ID=your_sheet_id
python orchestrator.py --yfinance --now
```

---

## Thresholds

Edit `config.py` to adjust the scoring thresholds:

```python
THRESHOLDS = {
    "dy_min":           2.5,   # Dividend Yield %
    "dgr_min":          5.0,   # 5yr Dividend Growth Rate %
    "payout_max":      75.0,   # Payout Ratio %
    "fcf_coverage_min": 1.2,   # FCF / Dividends paid
    "spread_min":      10.0,   # Upside to analyst target %
}
```
