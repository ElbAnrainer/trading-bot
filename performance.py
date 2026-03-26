import csv
import os
from collections import Counter, defaultdict
from statistics import mean


JOURNAL_CANDIDATES = [
    os.path.join("reports", "trading_journal.csv"),
    "trading_journal.csv",
]

BOX_WIDTH = 52


def _line(char="="):
    return char * BOX_WIDTH


def _print_box(title, lines):
    print("\n" + _line("="))
    print(title)
    print(_line("="))
    for line in lines:
        print(line)
    print(_line("="))


def _to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _find_journal_path():
    for path in JOURNAL_CANDIDATES:
        if os.path.exists(path):
            return path
    return JOURNAL_CANDIDATES[0]


def _load_journal_rows():
    path = _find_journal_path()
    if not os.path.exists(path):
        return []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _closed_trades(rows):
    out = []
    for row in rows:
        closed_trade = str(row.get("closed_trade", "")).strip().lower() == "true"
        if not closed_trade:
            continue

        pnl = _to_float(row.get("realized_pnl_eur", row.get("pnl_eur", 0.0)), 0.0)
        score = _to_float(row.get("score", 0.0), 0.0)

        out.append(
            {
                "symbol": (row.get("symbol") or "").strip(),
                "company": (row.get("company") or "").strip(),
                "signal": (row.get("signal") or "").strip(),
                "reason": (row.get("reason") or "").strip(),
                "pnl_eur": pnl,
                "score": score,
            }
        )
    return out


def _all_signals(rows):
    counts = Counter()
    for row in rows:
        signal = (row.get("signal") or "").strip().upper()
        if signal:
            counts[signal] += 1
    return counts


def _top_symbols(rows, limit=5):
    counts = Counter()
    names = {}

    for row in rows:
        symbol = (row.get("symbol") or "").strip()
        if not symbol:
            continue
        counts[symbol] += 1
        company = (row.get("company") or "").strip()
        if company:
            names[symbol] = company

    result = []
    for symbol, count in counts.most_common(limit):
        result.append(
            {
                "symbol": symbol,
                "company": names.get(symbol, symbol),
                "count": count,
            }
        )
    return result


def _score_validation_rows(trades):
    by_symbol = defaultdict(
        lambda: {
            "company": "",
            "scores": [],
            "pnls": [],
            "wins": 0,
            "trades": 0,
        }
    )

    for trade in trades:
        symbol = trade["symbol"] or "-"
        by_symbol[symbol]["company"] = trade.get("company") or symbol
        by_symbol[symbol]["scores"].append(trade["score"])
        by_symbol[symbol]["pnls"].append(trade["pnl_eur"])
        by_symbol[symbol]["trades"] += 1
        if trade["pnl_eur"] > 0:
            by_symbol[symbol]["wins"] += 1

    result_rows = []
    for symbol, data in by_symbol.items():
        trades_count = data["trades"]
        total_pnl = sum(data["pnls"])
        avg_score = mean(data["scores"]) if data["scores"] else 0.0
        hit_rate = (data["wins"] / trades_count * 100.0) if trades_count else 0.0

        result_rows.append(
            {
                "symbol": symbol,
                "company": data["company"],
                "avg_score": avg_score,
                "total_pnl": total_pnl,
                "trades": trades_count,
                "hit_rate": hit_rate,
            }
        )

    result_rows.sort(
        key=lambda x: (
            x["total_pnl"],
            x["hit_rate"],
            x["trades"],
            x["avg_score"],
        ),
        reverse=True,
    )
    return result_rows


def analyze_performance():
    rows = _load_journal_rows()
    trades = _closed_trades(rows)
    signal_counts = _all_signals(rows)

    closed_count = len(trades)
    wins = sum(1 for t in trades if t["pnl_eur"] > 0)
    losses = sum(1 for t in trades if t["pnl_eur"] < 0)
    total_pnl = sum(t["pnl_eur"] for t in trades)
    avg_trade = (total_pnl / closed_count) if closed_count else 0.0
    hit_rate = (wins / closed_count * 100.0) if closed_count else 0.0
    top_symbols = _top_symbols(rows, limit=5)
    score_rows = _score_validation_rows(trades)

    unique_symbols = len(
        {
            (row.get("symbol") or "").strip()
            for row in rows
            if (row.get("symbol") or "").strip()
        }
    )

    return {
        "journal_entries": len(rows),
        "buy_signals": signal_counts.get("BUY", 0),
        "sell_signals": signal_counts.get("SELL", 0),
        "watch_signals": signal_counts.get("WATCH", 0),
        "hold_signals": signal_counts.get("HOLD", 0),
        "unique_symbols": unique_symbols,
        "closed_trades": closed_count,
        "winning_trades": wins,
        "losing_trades": losses,
        "hit_rate": hit_rate,
        "realized_pnl": total_pnl,
        "avg_trade_pnl": avg_trade,
        "top_symbols": top_symbols,
        "score_validation": score_rows,
    }


def print_performance():
    summary = analyze_performance()

    summary_lines = [
        f"Journal-Einträge     : {summary['journal_entries']}",
        f"BUY Signale          : {summary['buy_signals']}",
        f"SELL Signale         : {summary['sell_signals']}",
        f"WATCH Signale        : {summary['watch_signals']}",
        f"HOLD Signale         : {summary['hold_signals']}",
        f"Aktien gesamt        : {summary['unique_symbols']}",
        "------------------------------",
        f"Geschlossene Trades  : {summary['closed_trades']}",
        f"Gewinntrades         : {summary['winning_trades']}",
        f"Verlusttrades        : {summary['losing_trades']}",
        f"Trefferquote         : {summary['hit_rate']:.2f} %",
        f"Realisierter P/L     : {summary['realized_pnl']:.2f} EUR",
        f"Ø Trade P/L          : {summary['avg_trade_pnl']:.2f} EUR",
    ]

    if summary["top_symbols"]:
        summary_lines.append("------------------------------")
        summary_lines.append("Top Aktien nach Häufigkeit:")
        for item in summary["top_symbols"]:
            summary_lines.append(
                f"  {item['symbol']} ({item['company']}): {item['count']}"
            )

    summary_lines.extend(
        [
            "------------------------------",
            "Hinweis: Diese Auswertung basiert ausschließlich auf Simulationsdaten.",
            "Es handelt sich nicht um Anlageberatung und nicht um echte Orderausführung.",
        ]
    )

    _print_box("SIMULATIONS-AUSWERTUNG", summary_lines)

    score_lines = [
        "Info:",
        "  Score   : Interne Bewertung der Aktie durch das Modell.",
        "            Höher = bessere Kombination aus Trend, Momentum und Qualität.",
        "  P/L     : Profit/Loss → Gewinn oder Verlust pro Aktie im Backtest.",
        "  Trades  : Anzahl abgeschlossener Trades (Kauf + Verkauf).",
        "  Treffer : Trefferquote → Anteil der Gewinntrades in Prozent.",
        "            Beispiel: 60% = 6 von 10 Trades waren profitabel.",
        "------------------------------",
    ]

    if not summary["score_validation"]:
        score_lines.append("Keine geschlossenen Trades für Score-Validierung vorhanden.")
    else:
        for row in summary["score_validation"][:10]:
            score_lines.append(
                f"{row['symbol']}: "
                f"Score={row['avg_score']:.2f} | "
                f"P/L={row['total_pnl']:.2f} EUR | "
                f"Trades={row['trades']} | "
                f"Treffer={row['hit_rate']:.2f}%"
            )

    _print_box("SCORE VALIDIERUNG", score_lines)

    return summary


if __name__ == "__main__":
    print_performance()
