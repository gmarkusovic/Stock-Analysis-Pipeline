"""
Free data source via yfinance. No API key required.
Mirrors the return shapes of the original sp_global and daloopa fetchers.
"""

import yfinance as yf


def _cashflow_row(cf, *candidates):
    """Return the first matching row from the cashflow DataFrame, or 0."""
    for key in candidates:
        if key in cf.index:
            val = cf.loc[key].iloc[0]
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return 0.0


def fetch_sp(ticker: str) -> dict:
    """
    Returns:
        price           float  current market price
        analyst_target  float  consensus 12-month price target
        payout_ratio    float  trailing payout ratio %
        annual_dividend float  trailing twelve-month dividend per share
    """
    t    = yf.Ticker(ticker)
    info = t.info

    price    = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
    target   = info.get("targetMeanPrice") or 0.0
    payout   = (info.get("payoutRatio") or 0.0) * 100     # yfinance: 0–1 decimal
    dividend = info.get("dividendRate") or info.get("trailingAnnualDividendRate") or 0.0

    return {
        "price":           float(price),
        "analyst_target":  float(target),
        "payout_ratio":    float(payout),
        "annual_dividend": float(dividend),
    }


def fetch_dalo(ticker: str) -> dict:
    """
    Returns:
        fcf              float  trailing FCF (USD, full value — not millions)
        dividends_paid   float  trailing dividends paid (USD, absolute value)
        dividend_history list   [{"year": int, "dps": float}, ...] last 6 years
    """
    t  = yf.Ticker(ticker)
    cf = t.cashflow

    fcf = _cashflow_row(cf, "Free Cash Flow")
    if fcf == 0.0:
        ocf   = _cashflow_row(cf, "Operating Cash Flow", "Total Cash From Operating Activities")
        capex = _cashflow_row(cf, "Capital Expenditure", "Capital Expenditures")
        fcf   = ocf + capex      # capex is negative in yfinance

    divs_paid = abs(_cashflow_row(
        cf,
        "Common Stock Dividend Paid",
        "Cash Dividends Paid",
        "Payment Of Dividends",
        "Dividends Paid",
    ))

    # Annual dividend per share — aggregate quarterly payments by calendar year
    raw_divs = t.dividends
    if not raw_divs.empty:
        annual = raw_divs.groupby(raw_divs.index.year).sum()
        history = [
            {"year": int(yr), "dps": float(dps)}
            for yr, dps in annual.tail(6).items()
        ]
    else:
        history = []

    return {
        "fcf":             float(fcf),
        "dividends_paid":  float(divs_paid),
        "dividend_history": history,
    }
