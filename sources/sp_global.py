"""
S&P Global Market Intelligence API fetcher.

Endpoints confirmed against S&P MI REST API v1:
  GET /v1/security/prices         → current price
  GET /v1/estimates/consensus     → analyst target, EPS
  GET /v1/company/ratios          → payout ratio, dividend per share

Docs: https://developer.spglobal.com/marketintelligence/docs
"""

import requests
from config import require_env

_BASE = "https://api.mi.spglobal.com/v1"


def _headers() -> dict:
    return {"Authorization": f"Bearer {require_env('SP_GLOBAL_API_KEY')}"}


def _get(path: str, params: dict) -> dict:
    resp = requests.get(f"{_BASE}{path}", headers=_headers(), params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch(ticker: str) -> dict:
    """
    Returns:
        price           float  current market price
        analyst_target  float  consensus 12-month price target
        payout_ratio    float  trailing payout ratio %
        annual_dividend float  trailing twelve-month dividend per share
    """
    price_data = _get("/security/prices", {"ticker": ticker, "fields": "lastPrice"})
    consensus   = _get("/estimates/consensus", {"ticker": ticker, "fields": "priceTarget"})
    ratios      = _get("/company/ratios", {"ticker": ticker, "fields": "payoutRatio,dividendPerShare"})

    return {
        "price":           float(price_data["lastPrice"]),
        "analyst_target":  float(consensus["priceTarget"]),
        "payout_ratio":    float(ratios["payoutRatio"]),
        "annual_dividend": float(ratios["dividendPerShare"]),
    }
