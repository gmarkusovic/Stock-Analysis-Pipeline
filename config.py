import os

THRESHOLDS = {
    "dy_min": 2.5,            # Dividend Yield %
    "dgr_min": 5.0,           # 5yr Dividend Growth Rate %
    "payout_max": 75.0,       # Payout Ratio %
    "fcf_coverage_min": 1.2,  # FCF / dividends paid
    "spread_min": 10.0,       # Upside to analyst target %
}

MAX_WORKERS = 10
SCHEDULE_CRON_DAY = "monday"
SCHEDULE_CRON_TIME = "23:00"


def require_env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val
