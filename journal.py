import csv
import os
from datetime import datetime, timezone

from config import TRADING_JOURNAL_CSV

JOURNAL_FILE = TRADING_JOURNAL_CSV
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


def _read_rows():
    with open(JOURNAL_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def _write_rows(rows):
    with open(JOURNAL_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in FIELDNAMES})


def _ensure_file():
    os.makedirs(os.path.dirname(JOURNAL_FILE), exist_ok=True)

    if not os.path.exists(JOURNAL_FILE):
        _write_rows([])
        return

    fieldnames, rows = _read_rows()

    if all(name in fieldnames for name in FIELDNAMES):
        return

    _write_rows(rows)


def backfill_missing_identifiers(resolve_identifiers_func):
    _ensure_file()

    _, rows = _read_rows()
    if not rows:
        return 0

    changed = 0
    resolved = {}

    for row in rows:
        current_isin = (row.get("isin") or "").strip()
        current_wkn = (row.get("wkn") or "").strip()

        if current_isin != "" and current_wkn != "":
            continue

        key = (row.get("symbol", ""), row.get("company", ""))
        if key not in resolved:
            resolved[key] = resolve_identifiers_func(row.get("symbol", ""), row.get("company", "")) or {}

        identifiers = resolved[key]
        new_isin = str(identifiers.get("isin", row.get("isin", "")) or "").strip() or "-"
        new_wkn = str(identifiers.get("wkn", row.get("wkn", "")) or "").strip() or "-"

        row_changed = False
        if current_isin == "" and new_isin != current_isin:
            row["isin"] = new_isin
            row_changed = True
        if current_wkn == "" and new_wkn != current_wkn:
            row["wkn"] = new_wkn
            row_changed = True
        if row_changed:
            changed += 1

    if changed:
        _write_rows(rows)

    return changed


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
