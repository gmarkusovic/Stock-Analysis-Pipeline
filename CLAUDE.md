# Stock Analysis Pipeline

Weekly automated pipeline that runs parallel subagents per company in a watchlist, evaluates each against a dividend/value framework, and consolidates results into a Google Sheet ranked by opportunity.

## Architecture

```
orchestrator.py
├── scheduler (runs every Monday 23:00)
├── subagent per ticker (parallel, ThreadPoolExecutor)
│   ├── fetch: yfinance (free) or mock (offline)
│   ├── calculate: spread vs analyst target
│   └── evaluate: DY, DGR, payout ratio, FCF
└── consolidator → Google Sheets
```

## Evaluation Framework

| Metric | Threshold | Source field |
|--------|-----------|--------------|
| DY | ≥ 2.5% | dividendRate / currentPrice |
| DGR | ≥ 5.0% | 5-yr CAGR of annual dividends |
| Payout Ratio | ≤ 75% | payoutRatio |
| FCF coverage | ≥ 1.2x | Free Cash Flow / Dividends Paid |
| Spread | ≥ 10% | (targetMeanPrice − price) / price |

Score = count of passing metrics (0–5).

## Project Structure

```
/
├── CLAUDE.md
├── orchestrator.py            # scheduler + launcher + consolidator
├── subagent.py                # single-ticker analysis
├── sources/
│   ├── yfinance_source.py     # live data via yfinance (free, no key)
│   ├── mock.py                # offline test data for all watchlist tickers
│   ├── sp_global.py           # S&P Global stub (paid, unused by default)
│   └── daloopa.py             # Daloopa stub (paid, unused by default)
├── output/
│   ├── gsheets.py             # Google Sheets writer (one tab per run)
│   └── gdoc.py                # Google Docs renderer (used for dry-run stdout)
├── watchlist.json
├── config.py                  # thresholds, env var refs, schedule
└── requirements.txt
```

## Watchlist Format

```json
[
  { "ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare" },
  { "ticker": "KO",  "name": "Coca-Cola",          "sector": "Consumer Staples" }
]
```

## Environment Variables

```
GOOGLE_SERVICE_ACCOUNT_JSON=   # path to service account JSON file
GOOGLE_SPREADSHEET_ID=         # target Google Spreadsheet ID
```

No API keys needed for data (yfinance is free).

## Usage

```bash
pip install -r requirements.txt

# Test — no credentials required
python orchestrator.py --mock --dry-run

# Live data, print to stdout (no Sheets write)
python orchestrator.py --yfinance --dry-run

# Live data → write to Google Sheets
python orchestrator.py --yfinance --now

# Scheduler mode (Monday 23:00, writes Sheets automatically)
python orchestrator.py
```

## Output: Google Sheets

- Tab `YYYY-MM-DD` created on each run (history preserved).
- Tab `Latest` always reflects the most recent run.
- Columns: Rank, Ticker, Name, Sector, Score, DY%, DGR%, Payout%, FCFcov, Spread%, Price, Target, DPS/yr, PASS/FAIL per criterion.

## Key Constraints

- Subagents run in parallel; orchestrator waits for all before writing.
- Failed tickers are marked DATA_ERROR and appended at the bottom of the sheet.
- Credentials never hardcoded; always from environment variables.
