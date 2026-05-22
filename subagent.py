"""
Single-ticker analysis unit. Called in parallel by the orchestrator.
"""

from __future__ import annotations
import math
from sources import sp_global, daloopa, mock
from config import THRESHOLDS


def _dgr(history: list[dict]) -> float | None:
    """5-year CAGR of dividend per share. Needs at least 2 data points."""
    valid = [h for h in history if h["dps"] > 0]
    if len(valid) < 2:
        return None
    n = len(valid) - 1
    return (math.pow(valid[-1]["dps"] / valid[0]["dps"], 1 / n) - 1) * 100


def _score(metrics: dict) -> tuple[int, dict]:
    t = THRESHOLDS
    checks = {
        "dy":            metrics["dy"]           >= t["dy_min"],
        "dgr":           (metrics["dgr"] or 0)   >= t["dgr_min"],
        "payout_ratio":  metrics["payout_ratio"] <= t["payout_max"],
        "fcf_coverage":  metrics["fcf_coverage"] >= t["fcf_coverage_min"],
        "spread":        metrics["spread"]        >= t["spread_min"],
    }
    return sum(checks.values()), checks


def analyze(entry: dict, use_mock: bool = False) -> dict:
    """
    Args:
        entry:    {"ticker": str, "name": str, "sector": str}
        use_mock: if True, use sources/mock.py instead of live APIs

    Returns dict with keys:
        ticker, name, sector, score (0-5), metrics, checks, status
        status: "ok" | "data_error"
        error: str (only if data_error)
    """
    ticker = entry["ticker"]

    try:
        if use_mock:
            sp   = mock.fetch_sp(ticker)
            dalo = mock.fetch_dalo(ticker)
        else:
            sp   = sp_global.fetch(ticker)
            dalo = daloopa.fetch(ticker)
    except Exception as exc:
        return {
            "ticker": ticker,
            "name":   entry["name"],
            "sector": entry["sector"],
            "score":  -1,
            "status": "data_error",
            "error":  str(exc),
        }

    dy  = (sp["annual_dividend"] / sp["price"]) * 100 if sp["price"] else 0
    dgr = _dgr(dalo["dividend_history"])
    fcf_coverage = dalo["fcf"] / dalo["dividends_paid"] if dalo["dividends_paid"] else 0
    spread = ((sp["analyst_target"] - sp["price"]) / sp["price"]) * 100 if sp["price"] else 0

    metrics = {
        "price":          sp["price"],
        "analyst_target": sp["analyst_target"],
        "annual_dividend": sp["annual_dividend"],
        "dy":             round(dy, 2),
        "dgr":            round(dgr, 2) if dgr is not None else None,
        "payout_ratio":   round(sp["payout_ratio"], 2),
        "fcf_coverage":   round(fcf_coverage, 2),
        "spread":         round(spread, 2),
    }

    score, checks = _score(metrics)

    return {
        "ticker":  ticker,
        "name":    entry["name"],
        "sector":  entry["sector"],
        "score":   score,
        "metrics": metrics,
        "checks":  checks,
        "status":  "ok",
    }
