"""
Entry point. Loads watchlist, runs subagents in parallel, writes Google Doc.

Usage:
    python orchestrator.py                      # start scheduler (runs every Monday 23:00)
    python orchestrator.py --now                # run immediately, write Google Doc
    python orchestrator.py --mock --dry-run     # full test with no credentials
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
from output import gdoc
from config import MAX_WORKERS, SCHEDULE_CRON_DAY, SCHEDULE_CRON_TIME


def load_watchlist() -> list[dict]:
    path = Path(__file__).parent / "watchlist.json"
    with open(path) as f:
        return json.load(f)


def run_pipeline(use_mock: bool = False, dry_run: bool = False):
    watchlist = load_watchlist()
    mode = " [MOCK]" if use_mock else ""
    print(f"[pipeline] Starting analysis for {len(watchlist)} tickers{mode}")

    results = []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(watchlist))) as pool:
        futures = {
            pool.submit(subagent.analyze, entry, use_mock): entry
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

    if dry_run:
        print("\n" + gdoc.render(results, run_date=date.today()))
        print("[pipeline] Dry-run complete — Google Doc not updated.")
    else:
        gdoc.write(results, run_date=date.today())
    print("[pipeline] Done.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--now",      action="store_true", help="Run immediately and exit")
    parser.add_argument("--mock",     action="store_true", help="Use mock data (no API keys needed)")
    parser.add_argument("--dry-run",  action="store_true", help="Print output to stdout, skip Google Doc")
    args = parser.parse_args()

    if args.now or args.mock or args.dry_run:
        run_pipeline(use_mock=args.mock, dry_run=args.dry_run)
        sys.exit(0)

    schedule.every().__getattr__(SCHEDULE_CRON_DAY).at(SCHEDULE_CRON_TIME).do(run_pipeline)
    print(f"[scheduler] Waiting — next run: {SCHEDULE_CRON_DAY} at {SCHEDULE_CRON_TIME}")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
