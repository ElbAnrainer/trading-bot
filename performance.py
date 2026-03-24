import csv
from collections import Counter, defaultdict
from pathlib import Path

from data_loader import load_ticker_metadata


JOURNAL_FILE_CANDIDATES = [
    Path("reports/trading_journal.csv"),
    Path("trading_journal.csv"),
]


def _find_journal_file():
    for path in JOURNAL_FILE_CANDIDATES:
        if path.exists():
            return path
    return JOURNAL_FILE_CANDIDATES[0]


def _to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_rows():
    journal_file = _find_journal_file()

    if not journal_file.exists():
        return []

    with open(journal_file, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _get_company_name(symbol, cache):
    if symbol not in cache:
        try:
            meta = load_ticker_metadata(symbol)
            cache[symbol] = meta.get("name", symbol)
        except Exception:
            cache[symbol] = symbol
    return cache[symbol]


def _format_symbol_with_name(symbol, cache):
    return f"{symbol} ({_get_company_name(symbol, cache)})"


def analyze_performance():
    rows = _load_rows()

    if not rows:
        return None

    stats = {
        "total_entries": len(rows),
        "buy_count": 0,
        "sell_count": 0,
        "watch_count": 0,
        "hold_count": 0,
        "unique_symbols": 0,
        "top_symbols": [],
        "top_winners": [],
        "top_losers": [],
        "closed_trades": 0,
        "win_trades": 0,
        "loss_trades": 0,
        "flat_trades": 0,
        "realized_pnl_eur": 0.0,
        "avg_trade_pnl_eur": 0.0,
        "hit_rate_pct": 0.0,
    }

    signal_counter = Counter()
    symbol_counter = Counter()
    symbol_pnl = defaultdict(float)

    for row in rows:
        signal = (row.get("signal") or "").strip().upper()
        symbol = (row.get("symbol") or "").strip()

        if signal:
            signal_counter[signal] += 1

        if symbol:
            symbol_counter[symbol] += 1

        is_closed_trade = str(row.get("closed_trade", "")).strip().lower() == "true"
        realized_pnl_eur = _to_float(row.get("realized_pnl_eur"), 0.0)

        if is_closed_trade:
            stats["closed_trades"] += 1
            stats["realized_pnl_eur"] += realized_pnl_eur

            if symbol:
                symbol_pnl[symbol] += realized_pnl_eur

            if realized_pnl_eur > 0:
                stats["win_trades"] += 1
            elif realized_pnl_eur < 0:
                stats["loss_trades"] += 1
            else:
                stats["flat_trades"] += 1

    stats["buy_count"] = signal_counter.get("BUY", 0)
    stats["sell_count"] = signal_counter.get("SELL", 0)
    stats["watch_count"] = signal_counter.get("WATCH", 0)
    stats["hold_count"] = signal_counter.get("HOLD", 0)
    stats["unique_symbols"] = len(symbol_counter)
    stats["top_symbols"] = symbol_counter.most_common(5)

    ranked_by_pnl = sorted(symbol_pnl.items(), key=lambda x: x[1], reverse=True)
    stats["top_winners"] = ranked_by_pnl[:5]
    stats["top_losers"] = sorted(symbol_pnl.items(), key=lambda x: x[1])[:5]

    if stats["closed_trades"] > 0:
        stats["avg_trade_pnl_eur"] = stats["realized_pnl_eur"] / stats["closed_trades"]
        stats["hit_rate_pct"] = (stats["win_trades"] / stats["closed_trades"]) * 100.0

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

    name_cache = {}

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

    print("Top Aktien nach Häufigkeit:")
    if stats["top_symbols"]:
        for sym, count in stats["top_symbols"]:
            label = _format_symbol_with_name(sym, name_cache)
            print(f"  {label}: {count}")
    else:
        print("  Keine Daten")

    print("------------------------------")
    print("Top Gewinner nach Sim-P/L:")
    winners_printed = False
    for sym, pnl in stats["top_winners"]:
        if pnl > 0:
            label = _format_symbol_with_name(sym, name_cache)
            print(f"  {label}: {pnl:.2f} EUR")
            winners_printed = True
    if not winners_printed:
        print("  Keine positiven Ergebnisse")

    print("------------------------------")
    print("Top Verlierer nach Sim-P/L:")
    losers_printed = False
    for sym, pnl in stats["top_losers"]:
        if pnl < 0:
            label = _format_symbol_with_name(sym, name_cache)
            print(f"  {label}: {pnl:.2f} EUR")
            losers_printed = True
    if not losers_printed:
        print("  Keine negativen Ergebnisse")

    print("------------------------------")
    print("Hinweis: Diese Auswertung basiert ausschließlich auf Simulationsdaten.")
    print("Es handelt sich nicht um Anlageberatung und nicht um echte Orderausführung.")
    print("==============================\n")
