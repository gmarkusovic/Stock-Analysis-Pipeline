"""
Entry point. Loads watchlist, runs subagents in parallel, writes output.

Usage:
    python orchestrator.py                           # scheduler, Monday 23:00
    python orchestrator.py --now                     # run now → Google Sheets
    python orchestrator.py --yfinance --dry-run      # live data, print to stdout
    python orchestrator.py --mock --dry-run          # no network, no keys needed
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import schedule
import time

import subagent
from output import gdoc, gsheets
from config import MAX_WORKERS, SCHEDULE_CRON_DAY, SCHEDULE_CRON_TIME


def load_watchlist() -> list[dict]:
    path = Path(__file__).parent / "watchlist.json"
    with open(path) as f:
        return json.load(f)


def run_pipeline(use_mock: bool = False, use_yfinance: bool = False, dry_run: bool = False):
    watchlist = load_watchlist()
    source = "MOCK" if use_mock else "YFINANCE" if use_yfinance else "LIVE"
    print(f"[pipeline] Starting — {len(watchlist)} tickers  source={source}")

    results = []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(watchlist))) as pool:
        futures = {
            pool.submit(subagent.analyze, entry, use_mock, use_yfinance): entry
            for entry in watchlist
        }
        for future in as_completed(futures):
            entry = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "ticker": entry["ticker"],
                    "name":   entry["name"],
                    "sector": entry["sector"],
                    "score":  -1,
                    "status": "data_error",
                    "error":  str(exc),
                }
            results.append(result)
            status = result["status"]
            score  = result.get("score", -1)
            print(f"  [{status.upper()}] {entry['ticker']}  score={score}")

    run_date = date.today()
    if dry_run:
        print("\n" + gdoc.render(results, run_date=run_date))
        print("[pipeline] Dry-run — no output written.")
    else:
        gsheets.write(results, run_date=run_date)

    print("[pipeline] Done.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--now",       action="store_true", help="Run immediately and exit")
    parser.add_argument("--mock",      action="store_true", help="Use mock data (offline)")
    parser.add_argument("--yfinance",  action="store_true", help="Use yfinance (free, no key)")
    parser.add_argument("--dry-run",   action="store_true", help="Print to stdout, skip Sheets write")
    args = parser.parse_args()

    if args.now or args.mock or args.yfinance or args.dry_run:
        run_pipeline(
            use_mock=args.mock,
            use_yfinance=args.yfinance,
            dry_run=args.dry_run,
        )
        sys.exit(0)

    schedule.every().__getattr__(SCHEDULE_CRON_DAY).at(SCHEDULE_CRON_TIME).do(run_pipeline, use_yfinance=True)
    print(f"[scheduler] Waiting — next run: {SCHEDULE_CRON_DAY} at {SCHEDULE_CRON_TIME}")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
