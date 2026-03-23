import csv
import os
from datetime import datetime

JOURNAL_FILE = "reports/trading_journal.csv"


def _ensure_file():
    if not os.path.exists(JOURNAL_FILE):
        os.makedirs(os.path.dirname(JOURNAL_FILE), exist_ok=True)
        with open(JOURNAL_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "symbol",
                "company",
                "signal",
                "price_eur",
                "score",
                "reason",
                "closed_trade",
                "realized_pnl_eur",
            ])


def log_trade_decision(
    symbol,
    company,
    signal,
    price_eur,
    score,
    reason,
    closed_trade=False,
    realized_pnl_eur=0.0,
):
    _ensure_file()

    with open(JOURNAL_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.utcnow().isoformat(),
            symbol,
            company,
            signal,
            round(price_eur, 2) if price_eur not in (None, "") else "",
            round(score, 2) if score not in (None, "") else "",
            reason,
            "true" if closed_trade else "false",
            round(realized_pnl_eur, 2) if realized_pnl_eur not in (None, "") else 0.0,
        ])
