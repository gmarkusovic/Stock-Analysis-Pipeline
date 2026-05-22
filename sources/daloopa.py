"""
Daloopa API fetcher.

Endpoints confirmed against Daloopa REST API:
  GET /v1/model/{ticker}/line_items   → structured financial model items

Docs: https://api.daloopa.com/docs
"""

import requests
from config import require_env

_BASE = "https://api.daloopa.com/v1"


def _headers() -> dict:
    return {"X-API-Key": require_env("DALOOPA_API_KEY")}


def _get(path: str, params: dict = None) -> dict:
    resp = requests.get(f"{_BASE}{path}", headers=_headers(), params=params or {}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch(ticker: str) -> dict:
    """
    Returns:
        fcf              float  trailing twelve-month Free Cash Flow (USD millions)
        dividends_paid   float  trailing twelve-month total dividends paid (USD millions)
        dividend_history list   [{"year": int, "dps": float}, ...] last 6 years, oldest first
    """
    items = _get(f"/model/{ticker}/line_items", {
        "items": "free_cash_flow,dividends_paid,dividend_per_share",
        "periods": "annual",
        "limit": 6,
    })

    years = sorted(items["periods"], key=lambda p: p["year"])

    fcf            = float(years[-1]["free_cash_flow"])
    dividends_paid = float(years[-1]["dividends_paid"])
    dividend_history = [
        {"year": p["year"], "dps": float(p["dividend_per_share"])}
        for p in years
    ]

    return {
        "fcf":             fcf,
        "dividends_paid":  dividends_paid,
        "dividend_history": dividend_history,
    }
