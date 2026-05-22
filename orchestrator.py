"""
Entry point. Loads watchlist, runs subagents in parallel, writes Google Doc.

Usage:
    python orchestrator.py          # start scheduler (runs every Monday 23:00)
    python orchestrator.py --now    # run immediately and exit
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


def run_pipeline():
    watchlist = load_watchlist()
    print(f"[pipeline] Starting analysis for {len(watchlist)} tickers")

    results = []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(watchlist))) as pool:
        futures = {pool.submit(subagent.analyze, entry): entry for entry in watchlist}
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

    gdoc.write(results, run_date=date.today())
    print("[pipeline] Done.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", action="store_true", help="Run immediately and exit")
    args = parser.parse_args()

    if args.now:
        run_pipeline()
        sys.exit(0)

    schedule.every().__getattr__(SCHEDULE_CRON_DAY).at(SCHEDULE_CRON_TIME).do(run_pipeline)
    print(f"[scheduler] Waiting — next run: {SCHEDULE_CRON_DAY} at {SCHEDULE_CRON_TIME}")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
