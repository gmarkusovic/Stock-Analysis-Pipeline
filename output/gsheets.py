"""
Writes analysis results to a single Google Sheet, appending rows on each run.
- First run: writes the header row, then the data rows.
- Subsequent runs: appends data rows below existing data (header not repeated).
- Column A is always the run date so every row is traceable.

Auth: Google service account with Sheets scope.
"""

from datetime import date
from config import require_env, THRESHOLDS

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_HEADERS = [
    "Date",
    "Rank", "Ticker", "Name", "Sector", "Score",
    "DY%", "DGR%", "Payout%", "FCFcov", "Spread%",
    "Price", "Target", "DPS/yr",
    "DY", "DGR", "Payout", "FCF", "Spread",
]


def _service():
    import httplib2
    import google_auth_httplib2
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    import os
    sa_path = require_env("GOOGLE_SERVICE_ACCOUNT_JSON")
    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=_SCOPES)
    # SSL verification can be disabled for environments with intercepting proxies (e.g. Claude Code web)
    no_verify = os.getenv("DISABLE_SSL_VERIFY", "0") == "1"
    http = httplib2.Http(disable_ssl_certificate_validation=no_verify)
    authorized_http = google_auth_httplib2.AuthorizedHttp(creds, http=http)
    return build("sheets", "v4", http=authorized_http, cache_discovery=False)


def _pf(value: bool) -> str:
    return "✓" if value else "✗"


def _build_data_rows(results: list[dict], run_date: date) -> list[list]:
    """Returns only data rows (no header). Each row starts with the run date."""
    ok     = [r for r in results if r["status"] == "ok"]
    errors = [r for r in results if r["status"] == "data_error"]
    ok.sort(key=lambda r: (r["score"], r["metrics"]["spread"]), reverse=True)

    date_str = run_date.isoformat()
    rows = []

    for i, r in enumerate(ok, 1):
        m = r["metrics"]
        c = r["checks"]
        dgr_str = f"{m['dgr']:.2f}" if m["dgr"] is not None else "N/A"
        rows.append([
            date_str,
            i,
            r["ticker"],
            r["name"],
            r["sector"],
            f"{r['score']}/5",
            round(m["dy"], 2),
            dgr_str,
            round(m["payout_ratio"], 1),
            round(m["fcf_coverage"], 2),
            round(m["spread"], 1),
            round(m["price"], 2),
            round(m["analyst_target"], 2),
            round(m["annual_dividend"], 2),
            _pf(c["dy"]),
            _pf(c["dgr"]),
            _pf(c["payout_ratio"]),
            _pf(c["fcf_coverage"]),
            _pf(c["spread"]),
        ])

    for r in errors:
        rows.append([
            date_str, "ERR", r["ticker"], r["name"], r["sector"],
            "", "", "", "", "", "", "", "", "", "", "", "", "", r["error"],
        ])

    return rows


def _has_header(svc, spreadsheet_id: str, sheet_name: str) -> bool:
    """True if cell A1 already contains the header label."""
    result = svc.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1",
    ).execute()
    values = result.get("values", [])
    return bool(values) and values[0][0] == "Date"


def write(results: list[dict], run_date: date | None = None, sheet_name: str = "Analysis"):
    if run_date is None:
        run_date = date.today()

    spreadsheet_id = require_env("GOOGLE_SPREADSHEET_ID")
    svc = _service()

    if not _has_header(svc, spreadsheet_id, sheet_name):
        svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!A1",
            valueInputOption="RAW",
            body={"values": [_HEADERS]},
        ).execute()

    rows = _build_data_rows(results, run_date)
    svc.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows},
    ).execute()

    ok_count = sum(1 for r in results if r["status"] == "ok")
    print(f"Google Sheets updated: {ok_count}/{len(results)} rows appended  [{run_date.isoformat()}]")
