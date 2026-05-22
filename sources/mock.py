"""
Mock data for offline testing. Mirrors the return shapes of sp_global.fetch()
and daloopa.fetch() with realistic but fabricated numbers.

Expected scoring outcomes (score/5):
  JNJ  5/5  KO 5/5  XOM 5/5  ABBV 5/5  PG 4/5  VZ 3/5  T 2/5  MMM 0/5
"""

_SP = {
    "JNJ":  {"price": 151.00, "analyst_target": 175.00, "payout_ratio": 45.2, "annual_dividend": 4.76},
    "KO":   {"price":  63.00, "analyst_target":  72.00, "payout_ratio": 71.9, "annual_dividend": 1.94},
    "PG":   {"price": 155.00, "analyst_target": 165.00, "payout_ratio": 60.0, "annual_dividend": 4.00},
    "ABBV": {"price": 175.00, "analyst_target": 195.00, "payout_ratio": 64.1, "annual_dividend": 6.20},
    "MMM":  {"price": 125.00, "analyst_target": 130.00, "payout_ratio": 79.5, "annual_dividend": 3.02},
    "T":    {"price":  19.00, "analyst_target":  24.00, "payout_ratio": 84.7, "annual_dividend": 1.11},
    "VZ":   {"price":  41.00, "analyst_target":  48.00, "payout_ratio": 54.8, "annual_dividend": 2.71},
    "XOM":  {"price": 113.00, "analyst_target": 128.00, "payout_ratio": 40.8, "annual_dividend": 4.48},
}

# FCF and dividends_paid in USD millions. dividend_history: 6 annual points (2020-2025).
_DALO = {
    "JNJ": {
        "fcf": 18_000, "dividends_paid": 8_571,
        "dividend_history": [
            {"year": 2020, "dps": 3.98},
            {"year": 2021, "dps": 4.19},
            {"year": 2022, "dps": 4.45},
            {"year": 2023, "dps": 4.52},
            {"year": 2024, "dps": 4.64},
            {"year": 2025, "dps": 4.76},
        ],
    },
    "KO": {
        "fcf": 9_800, "dividends_paid": 7_000,
        "dividend_history": [
            {"year": 2020, "dps": 1.48},
            {"year": 2021, "dps": 1.56},
            {"year": 2022, "dps": 1.65},
            {"year": 2023, "dps": 1.74},
            {"year": 2024, "dps": 1.84},
            {"year": 2025, "dps": 1.94},
        ],
    },
    "PG": {
        "fcf": 14_000, "dividends_paid": 9_396,
        "dividend_history": [
            {"year": 2020, "dps": 3.02},
            {"year": 2021, "dps": 3.19},
            {"year": 2022, "dps": 3.38},
            {"year": 2023, "dps": 3.58},
            {"year": 2024, "dps": 3.79},
            {"year": 2025, "dps": 4.00},
        ],
    },
    "ABBV": {
        "fcf": 22_000, "dividends_paid": 13_750,
        "dividend_history": [
            {"year": 2020, "dps": 4.18},
            {"year": 2021, "dps": 4.53},
            {"year": 2022, "dps": 4.90},
            {"year": 2023, "dps": 5.31},
            {"year": 2024, "dps": 5.75},
            {"year": 2025, "dps": 6.20},
        ],
    },
    "MMM": {
        "fcf": 1_500, "dividends_paid": 1_667,
        "dividend_history": [
            {"year": 2020, "dps": 5.88},
            {"year": 2021, "dps": 5.92},
            {"year": 2022, "dps": 5.96},
            {"year": 2023, "dps": 6.00},
            {"year": 2024, "dps": 3.00},  # dividend cut
            {"year": 2025, "dps": 3.02},
        ],
    },
    "T": {
        "fcf": 8_767, "dividends_paid": 7_970,
        "dividend_history": [
            {"year": 2020, "dps": 2.08},
            {"year": 2021, "dps": 2.08},
            {"year": 2022, "dps": 1.11},  # dividend cut
            {"year": 2023, "dps": 1.11},
            {"year": 2024, "dps": 1.11},
            {"year": 2025, "dps": 1.11},
        ],
    },
    "VZ": {
        "fcf": 11_979, "dividends_paid": 11_409,
        "dividend_history": [
            {"year": 2020, "dps": 2.46},
            {"year": 2021, "dps": 2.51},
            {"year": 2022, "dps": 2.56},
            {"year": 2023, "dps": 2.61},
            {"year": 2024, "dps": 2.66},
            {"year": 2025, "dps": 2.71},
        ],
    },
    "XOM": {
        "fcf": 56_070, "dividends_paid": 20_025,
        "dividend_history": [
            {"year": 2020, "dps": 3.48},
            {"year": 2021, "dps": 3.52},
            {"year": 2022, "dps": 3.64},
            {"year": 2023, "dps": 3.80},
            {"year": 2024, "dps": 3.99},
            {"year": 2025, "dps": 4.48},
        ],
    },
}


def fetch_sp(ticker: str) -> dict:
    if ticker not in _SP:
        raise ValueError(f"[mock] No data for {ticker}")
    return dict(_SP[ticker])


def fetch_dalo(ticker: str) -> dict:
    if ticker not in _DALO:
        raise ValueError(f"[mock] No data for {ticker}")
    d = _DALO[ticker]
    return {
        "fcf":             d["fcf"],
        "dividends_paid":  d["dividends_paid"],
        "dividend_history": [dict(p) for p in d["dividend_history"]],
    }
