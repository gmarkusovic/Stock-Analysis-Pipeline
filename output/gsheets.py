"""
Writes analysis results to a single Google Sheet, appending rows on each run.
- First run: writes the header row, then the data rows.
- Subsequent runs: appends data rows below existing data (header not repeated).
- Column A is always the run date so every row is traceable.

Auth: Google service account with Sheets scope.
"""

import math
from datetime import date
from config import require_env, THRESHOLDS


def _clean(val):
    """Replace NaN/inf (invalid JSON) with 'N/A' so Sheets API never chokes."""
    if isinstance(val, float) and not math.isfinite(val):
        return "N/A"
    return val

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_HEADERS = [
    "Date",
    "Rank", "Ticker", "Name", "Sector", "Score",
    "DY%", "DGR%", "Payout%", "FCFcov", "Spread%",
    "Price", "Target", "DPS/yr",
    "DY", "DGR", "Payout", "FCF", "Spread",
]


def _build_info_from_parts(os, base64) -> dict | None:
    """Reconstruct service account info from individual env vars (iPad-friendly secrets)."""
    p1 = os.getenv("GOOGLE_PRIVATE_KEY_P1", "")
    p2 = os.getenv("GOOGLE_PRIVATE_KEY_P2", "")
    email = os.getenv("GOOGLE_CLIENT_EMAIL", "")
    if not (p1 and email):
        return None
    private_key = base64.b64decode(p1 + p2).decode("utf-8")
    return {
        "type": "service_account",
        "project_id": "stock-pipeline-497122",
        "private_key_id": "485aeb2db1890c4a2b3a84e095607b74cc342450",
        "private_key": private_key,
        "client_email": email,
        "client_id": "104351734846412693077",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def _service():
    import json, os, base64
    import httplib2, google_auth_httplib2
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    info = None

    # Priority 1: individual secrets (iPad-friendly, 3 short strings)
    info = _build_info_from_parts(os, base64)

    # Priority 2: full JSON string or base64-encoded JSON (single secret)
    if not info:
        sa_content = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        for attempt in (sa_content, None):
            try:
                info = json.loads(attempt if attempt is not None else base64.b64decode(sa_content))
                break
            except Exception:
                pass

    # Priority 3: file path
    if not info:
        sa_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        if sa_path:
            creds = service_account.Credentials.from_service_account_file(sa_path, scopes=_SCOPES)
        else:
            raise EnvironmentError(
                "No Google credentials found. Set GOOGLE_PRIVATE_KEY_P1 + GOOGLE_PRIVATE_KEY_P2 + "
                "GOOGLE_CLIENT_EMAIL, or GOOGLE_SERVICE_ACCOUNT_JSON."
            )
    else:
        creds = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)

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
    ok.sort(key=lambda r: (r["score"], 0 if not math.isfinite(r["metrics"]["spread"] or 0) else r["metrics"]["spread"]), reverse=True)

    date_str = run_date.isoformat()
    rows = []

    for i, r in enumerate(ok, 1):
        m = r["metrics"]
        c = r["checks"]
        dgr_val = m["dgr"]
        dgr_str = f"{dgr_val:.2f}" if (dgr_val is not None and math.isfinite(dgr_val)) else "N/A"
        rows.append([
            date_str,
            i,
            r["ticker"],
            r["name"],
            r["sector"],
            f"{r['score']}/5",
            _clean(round(m["dy"], 2)),
            dgr_str,
            _clean(round(m["payout_ratio"], 1)),
            _clean(round(m["fcf_coverage"], 2)),
            _clean(round(m["spread"], 1)),
            _clean(round(m["price"], 2)),
            _clean(round(m["analyst_target"], 2)),
            _clean(round(m["annual_dividend"], 2)),
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


def _get_all_rows(svc, spreadsheet_id: str, sheet_name: str) -> list[list]:
    result = svc.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'",
    ).execute()
    return result.get("values", [])


def _rewrite_sheet(svc, spreadsheet_id: str, sheet_name: str, rows: list[list]):
    svc.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"'{sheet_name}'"
    ).execute()
    if rows:
        svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!A1",
            valueInputOption="RAW",
            body={"values": rows},
        ).execute()


def write(results: list[dict], run_date: date | None = None, sheet_name: str = "Analysis"):
    if run_date is None:
        run_date = date.today()

    date_str = run_date.isoformat()
    spreadsheet_id = require_env("GOOGLE_SPREADSHEET_ID")
    svc = _service()

    # Load existing rows, strip any rows for today (idempotent re-runs)
    existing = _get_all_rows(svc, spreadsheet_id, sheet_name)
    if existing:
        header = existing[0]
        kept = [r for r in existing[1:] if r and r[0] != date_str]
    else:
        header = _HEADERS
        kept = []

    new_rows = _build_data_rows(results, run_date)
    final = [header] + kept + new_rows

    _rewrite_sheet(svc, spreadsheet_id, sheet_name, final)

    ok_count = sum(1 for r in results if r["status"] == "ok")
    print(f"Google Sheets updated: {ok_count}/{len(results)} rows written  [{date_str}]")


def clear_and_reset(sheet_name: str = "Analysis"):
    """Utility: wipe the sheet and write only the header. Run once to clean up."""
    spreadsheet_id = require_env("GOOGLE_SPREADSHEET_ID")
    svc = _service()
    _rewrite_sheet(svc, spreadsheet_id, sheet_name, [_HEADERS])
    print(f"Sheet '{sheet_name}' cleared.")


