# Stock Analysis Pipeline

Weekly automated pipeline that runs parallel subagents per company in a watchlist, evaluates each against a dividend/value framework, and consolidates results into a Google Doc ranked by opportunity.

## Architecture

```
orchestrator.py
├── scheduler (runs every Monday night)
├── subagent per ticker (parallel)
│   ├── fetch: S&P Global + Daloopa
│   ├── calculate: spread vs analyst target
│   └── evaluate: DY, DGR, payout ratio, FCF
└── consolidator → Google Doc
```

## Evaluation Framework

| Metric | Description |
|--------|-------------|
| DY | Dividend Yield vs sector median |
| DGR | 5-yr Dividend Growth Rate |
| Payout Ratio | Target < 75% |
| FCF | Free Cash Flow coverage of dividend |
| Spread | (Analyst target - current price) / current price |

A ticker scores 1 point per metric that passes its threshold. Max score = 5.

## Project Structure

```
/
├── CLAUDE.md
├── orchestrator.py        # scheduler + subagent launcher + consolidator
├── subagent.py            # single-ticker analysis logic
├── sources/
│   ├── sp_global.py       # S&P Global data fetcher
│   └── daloopa.py         # Daloopa data fetcher
├── output/
│   └── gdoc.py            # Google Docs writer
├── watchlist.json         # list of tickers to analyze
└── config.py              # thresholds, credentials refs, schedule
```

## Watchlist Format

```json
[
  { "ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare" },
  { "ticker": "KO",  "name": "Coca-Cola",          "sector": "Consumer Staples" }
]
```

## Data Sources

- **S&P Global**: fundamentals (EPS, revenue, analyst targets, payout ratio)
- **Daloopa**: structured financial model data (FCF, DGR, balance sheet items)
- Both accessed via their respective APIs; credentials in environment variables.

## Environment Variables

```
SP_GLOBAL_API_KEY=
DALOOPA_API_KEY=
GOOGLE_SERVICE_ACCOUNT_JSON=   # path to service account file
GOOGLE_DOC_ID=                 # target Google Doc to overwrite
```

## Output

Google Doc overwritten every run with:
1. Run date and watchlist size
2. Ranked table (score desc, then spread desc)
3. Per-ticker detail block: metrics, analyst target, spread, pass/fail per criterion

## Schedule

- Runs: Monday 23:00 local time (cron or cloud scheduler)
- Available: Tuesday morning with results ready
- Trigger manually: `python orchestrator.py --now`

## Key Constraints

- Subagents run in parallel (one per ticker); orchestrator waits for all before writing output.
- If a data source fails for a ticker, that ticker is marked `DATA_ERROR` and included at the bottom of the doc.
- No historical storage; each run is self-contained and overwrites the previous Google Doc.
- Credentials are never hardcoded; always read from environment variables.
