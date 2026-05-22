"""
Writes analysis results to Google Sheets.
- Creates a tab named YYYY-MM-DD for every run (history preserved).
- Always overwrites a "Latest" tab for quick access.

Auth: Google service account with Sheets scope.
"""

from datetime import date
from config import require_env, THRESHOLDS

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_HEADERS = [
    "Rank", "Ticker", "Name", "Sector", "Score",
    "DY%", "DGR%", "Payout%", "FCFcov", "Spread%",
    "Price", "Target", "DPS/yr",
    "DY", "DGR", "Payout", "FCF", "Spread",     # PASS/FAIL columns
]


def _service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    sa_path = require_env("GOOGLE_SERVICE_ACCOUNT_JSON")
    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=_SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _pf(value: bool) -> str:
    return "✓" if value else "✗"


def _build_rows(results: list[dict], run_date: date) -> list[list]:
    ok     = [r for r in results if r["status"] == "ok"]
    errors = [r for r in results if r["status"] == "data_error"]
    ok.sort(key=lambda r: (r["score"], r["metrics"]["spread"]), reverse=True)

    rows = [_HEADERS]

    for i, r in enumerate(ok, 1):
        m = r["metrics"]
        c = r["checks"]
        dgr_str = f"{m['dgr']:.2f}" if m["dgr"] is not None else "N/A"
        rows.append([
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

    if errors:
        rows.append([])
        rows.append(["", "DATA ERRORS"])
        for r in errors:
            rows.append(["", r["ticker"], r["name"], "", "", "", "", "", "", "", "", "", "", r["error"]])

    rows.append([])
    rows.append([
        f"Run: {run_date.isoformat()} | "
        f"DY≥{THRESHOLDS['dy_min']}%  "
        f"DGR≥{THRESHOLDS['dgr_min']}%  "
        f"Payout≤{THRESHOLDS['payout_max']}%  "
        f"FCFcov≥{THRESHOLDS['fcf_coverage_min']}x  "
        f"Spread≥{THRESHOLDS['spread_min']}%"
    ])

    return rows


def _ensure_sheet(svc, spreadsheet_id: str, title: str) -> int:
    """Return sheetId for `title`, creating it if needed."""
    meta = svc.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in meta["sheets"]:
        if sheet["properties"]["title"] == title:
            return sheet["properties"]["sheetId"]

    resp = svc.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
    ).execute()
    return resp["replies"][0]["addSheet"]["properties"]["sheetId"]


def _write_tab(svc, spreadsheet_id: str, tab: str, rows: list[list]):
    range_name = f"'{tab}'!A1"
    svc.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"'{tab}'",
    ).execute()
    svc.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()


def write(results: list[dict], run_date: date | None = None):
    if run_date is None:
        run_date = date.today()

    spreadsheet_id = require_env("GOOGLE_SPREADSHEET_ID")
    svc  = _service()
    rows = _build_rows(results, run_date)

    tab_name = run_date.isoformat()
    _ensure_sheet(svc, spreadsheet_id, tab_name)
    _ensure_sheet(svc, spreadsheet_id, "Latest")

    _write_tab(svc, spreadsheet_id, tab_name, rows)
    _write_tab(svc, spreadsheet_id, "Latest",  rows)

    ok_count = sum(1 for r in results if r["status"] == "ok")
    print(f"Google Sheets updated: tab '{tab_name}'  ({ok_count}/{len(results)} tickers OK)")
