"""
Overwrites the target Google Doc with the ranked analysis results.
Uses a Google service account for authentication.
"""

import json
from datetime import date
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import require_env, THRESHOLDS

_SCOPES = ["https://www.googleapis.com/auth/documents"]


def _service():
    sa_path = require_env("GOOGLE_SERVICE_ACCOUNT_JSON")
    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=_SCOPES)
    return build("docs", "v1", credentials=creds, cache_discovery=False)


def _clear_and_insert(svc, doc_id: str, text: str):
    doc = svc.documents().get(documentId=doc_id).execute()
    body_end = doc["body"]["content"][-1]["endIndex"] - 1

    requests_batch = []
    if body_end > 1:
        requests_batch.append({
            "deleteContentRange": {
                "range": {"startIndex": 1, "endIndex": body_end}
            }
        })
    requests_batch.append({
        "insertText": {"location": {"index": 1}, "text": text}
    })

    svc.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests_batch},
    ).execute()


def _pass_fail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def _render(results: list[dict], run_date: date) -> str:
    ok     = [r for r in results if r["status"] == "ok"]
    errors = [r for r in results if r["status"] == "data_error"]

    ok.sort(key=lambda r: (r["score"], r["metrics"]["spread"]), reverse=True)

    lines = [
        f"Stock Analysis Pipeline — {run_date.isoformat()}",
        f"Watchlist: {len(results)} tickers  |  OK: {len(ok)}  |  Errors: {len(errors)}",
        f"Thresholds: DY≥{THRESHOLDS['dy_min']}%  DGR≥{THRESHOLDS['dgr_min']}%  "
        f"Payout≤{THRESHOLDS['payout_max']}%  FCF≥{THRESHOLDS['fcf_coverage_min']}x  "
        f"Spread≥{THRESHOLDS['spread_min']}%",
        "",
        "── RANKING ────────────────────────────────────────────────────────────────",
        f"{'#':<3} {'Ticker':<6} {'Name':<25} {'Score':<6} {'DY%':<7} {'DGR%':<7} "
        f"{'Payout%':<9} {'FCFcov':<8} {'Spread%':<9} {'Sector'}",
        "─" * 100,
    ]

    for i, r in enumerate(ok, 1):
        m = r["metrics"]
        dgr_str = f"{m['dgr']:.1f}" if m["dgr"] is not None else "N/A"
        lines.append(
            f"{i:<3} {r['ticker']:<6} {r['name']:<25} {r['score']}/5   "
            f"{m['dy']:<7.1f} {dgr_str:<7} {m['payout_ratio']:<9.1f} "
            f"{m['fcf_coverage']:<8.2f} {m['spread']:<9.1f} {r['sector']}"
        )

    lines += ["", "── DETAIL ─────────────────────────────────────────────────────────────────"]

    for r in ok:
        m = r["metrics"]
        c = r["checks"]
        dgr_str = f"{m['dgr']:.2f}%" if m["dgr"] is not None else "N/A"
        lines += [
            "",
            f"{r['ticker']} — {r['name']} ({r['sector']})   Score: {r['score']}/5",
            f"  Price: ${m['price']:.2f}   Target: ${m['analyst_target']:.2f}   "
            f"Spread: {m['spread']:+.1f}%   Dividend: ${m['annual_dividend']:.2f}/yr",
            f"  DY:         {m['dy']:.2f}%   [{_pass_fail(c['dy'])}  ≥{THRESHOLDS['dy_min']}%]",
            f"  DGR (5yr):  {dgr_str}   [{_pass_fail(c['dgr'])}  ≥{THRESHOLDS['dgr_min']}%]",
            f"  Payout:     {m['payout_ratio']:.1f}%   [{_pass_fail(c['payout_ratio'])}  ≤{THRESHOLDS['payout_max']}%]",
            f"  FCF cov:    {m['fcf_coverage']:.2f}x   [{_pass_fail(c['fcf_coverage'])}  ≥{THRESHOLDS['fcf_coverage_min']}x]",
            f"  Spread:     {m['spread']:+.1f}%   [{_pass_fail(c['spread'])}  ≥{THRESHOLDS['spread_min']}%]",
        ]

    if errors:
        lines += [
            "",
            "── DATA ERRORS ────────────────────────────────────────────────────────────",
        ]
        for r in errors:
            lines.append(f"  {r['ticker']} ({r['name']}): {r['error']}")

    return "\n".join(lines) + "\n"


def write(results: list[dict], run_date: date | None = None):
    if run_date is None:
        run_date = date.today()

    doc_id = require_env("GOOGLE_DOC_ID")
    svc    = _service()
    text   = _render(results, run_date)
    _clear_and_insert(svc, doc_id, text)
    print(f"Google Doc updated: {len(results)} tickers, {sum(1 for r in results if r['status'] == 'ok')} OK")
