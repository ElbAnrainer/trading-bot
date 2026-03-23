import csv
from collections import defaultdict

JOURNAL_FILE = "reports/trading_journal.csv"


def load_journal():
    try:
        with open(JOURNAL_FILE, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


def _to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def analyze_performance():
    data = load_journal()

    if not data:
        return None

    stats = {
        "total_entries": len(data),
        "buy_count": 0,
        "sell_count": 0,
        "watch_count": 0,
        "hold_count": 0,
        "unique_symbols": 0,
        "top_symbols": [],
        "closed_trades": 0,
        "win_trades": 0,
        "loss_trades": 0,
        "flat_trades": 0,
        "realized_pnl_eur": 0.0,
        "avg_trade_pnl_eur": 0.0,
        "hit_rate_pct": 0.0,
    }

    symbol_count = defaultdict(int)

    for row in data:
        signal = (row.get("signal") or "").upper().strip()
        symbol = (row.get("symbol") or "").strip()
        realized_pnl_eur = _to_float(row.get("realized_pnl_eur"), 0.0)
        is_closed_trade = str(row.get("closed_trade", "")).strip().lower() == "true"

        if symbol:
            symbol_count[symbol] += 1

        if signal == "BUY":
            stats["buy_count"] += 1
        elif signal == "SELL":
            stats["sell_count"] += 1
        elif signal == "WATCH":
            stats["watch_count"] += 1
        elif signal == "HOLD":
            stats["hold_count"] += 1

        if is_closed_trade:
            stats["closed_trades"] += 1
            stats["realized_pnl_eur"] += realized_pnl_eur

            if realized_pnl_eur > 0:
                stats["win_trades"] += 1
            elif realized_pnl_eur < 0:
                stats["loss_trades"] += 1
            else:
                stats["flat_trades"] += 1

    stats["unique_symbols"] = len(symbol_count)
    stats["top_symbols"] = sorted(symbol_count.items(), key=lambda x: x[1], reverse=True)[:5]

    if stats["closed_trades"] > 0:
        stats["avg_trade_pnl_eur"] = stats["realized_pnl_eur"] / stats["closed_trades"]
        stats["hit_rate_pct"] = (stats["win_trades"] / stats["closed_trades"]) * 100

    return stats


def print_performance():
    stats = analyze_performance()

    if not stats:
        print("\n==============================")
        print("SIMULATIONS-AUSWERTUNG")
        print("------------------------------")
        print("Keine Daten im Simulationsjournal.")
        print("==============================\n")
        return

    print("\n==============================")
    print("SIMULATIONS-AUSWERTUNG")
    print("------------------------------")
    print(f"Journal-Einträge     : {stats['total_entries']}")
    print(f"BUY Signale          : {stats['buy_count']}")
    print(f"SELL Signale         : {stats['sell_count']}")
    print(f"WATCH Signale        : {stats['watch_count']}")
    print(f"HOLD Signale         : {stats['hold_count']}")
    print(f"Aktien gesamt        : {stats['unique_symbols']}")
    print("------------------------------")
    print(f"Geschlossene Trades  : {stats['closed_trades']}")
    print(f"Gewinntrades         : {stats['win_trades']}")
    print(f"Verlusttrades        : {stats['loss_trades']}")
    print(f"Trefferquote         : {stats['hit_rate_pct']:.2f} %")
    print(f"Realisierter P/L     : {stats['realized_pnl_eur']:.2f} EUR")
    print(f"Ø Trade P/L          : {stats['avg_trade_pnl_eur']:.2f} EUR")
    print("------------------------------")
    print("Top Aktien:")
    for sym, count in stats["top_symbols"]:
        print(f"  {sym}: {count}")
    print("------------------------------")
    print("Hinweis: Diese Auswertung basiert ausschließlich auf Simulationsdaten.")
    print("Es handelt sich nicht um Anlageberatung und nicht um echte Orderausführung.")
    print("==============================\n")
