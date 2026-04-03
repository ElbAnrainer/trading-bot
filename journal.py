import csv
import os
from datetime import datetime, timezone

JOURNAL_FILE = "reports/trading_journal.csv"
FIELDNAMES = [
    "timestamp",
    "symbol",
    "company",
    "isin",
    "wkn",
    "signal",
    "price_eur",
    "score",
    "reason",
    "closed_trade",
    "realized_pnl_eur",
]


def _ensure_file():
    os.makedirs(os.path.dirname(JOURNAL_FILE), exist_ok=True)

    if not os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
        return

    with open(JOURNAL_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if all(name in fieldnames for name in FIELDNAMES):
        return

    with open(JOURNAL_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in FIELDNAMES})


def log_trade_decision(
    symbol,
    company,
    isin,
    wkn,
    signal,
    price_eur,
    score,
    reason,
    closed_trade=False,
    realized_pnl_eur=0.0,
):
    _ensure_file()

    with open(JOURNAL_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "company": company,
                "isin": isin,
                "wkn": wkn,
                "signal": signal,
                "price_eur": round(price_eur, 2) if price_eur not in (None, "") else "",
                "score": round(score, 2) if score not in (None, "") else "",
                "reason": reason,
                "closed_trade": "true" if closed_trade else "false",
                "realized_pnl_eur": round(realized_pnl_eur, 2) if realized_pnl_eur not in (None, "") else 0.0,
            }
        )
