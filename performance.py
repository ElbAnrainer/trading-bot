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
        "per_symbol": {},
        "score_validation": [],
        "closed_trades": 0,
        "win_trades": 0,
        "loss_trades": 0,
        "realized_pnl_eur": 0.0,
        "avg_trade_pnl_eur": 0.0,
        "hit_rate_pct": 0.0,
    }

    signal_counter = Counter()
    symbol_counter = Counter()

    per_symbol = defaultdict(lambda: {
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "pnl": 0.0,
        "scores": [],
    })

    for row in rows:
        signal = (row.get("signal") or "").strip().upper()
        symbol = (row.get("symbol") or "").strip()
        score = _to_float(row.get("score"), None)

        if signal:
            signal_counter[signal] += 1

        if symbol:
            symbol_counter[symbol] += 1

        is_closed_trade = str(row.get("closed_trade", "")).strip().lower() == "true"
        pnl = _to_float(row.get("realized_pnl_eur"), 0.0)

        if symbol and score is not None:
            per_symbol[symbol]["scores"].append(score)

        if is_closed_trade:
            stats["closed_trades"] += 1
            stats["realized_pnl_eur"] += pnl

            if symbol:
                ps = per_symbol[symbol]
                ps["trades"] += 1
                ps["pnl"] += pnl

                if pnl > 0:
                    ps["wins"] += 1
                    stats["win_trades"] += 1
                elif pnl < 0:
                    ps["losses"] += 1
                    stats["loss_trades"] += 1

    stats["buy_count"] = signal_counter.get("BUY", 0)
    stats["sell_count"] = signal_counter.get("SELL", 0)
    stats["watch_count"] = signal_counter.get("WATCH", 0)
    stats["hold_count"] = signal_counter.get("HOLD", 0)
    stats["unique_symbols"] = len(symbol_counter)
    stats["top_symbols"] = symbol_counter.most_common(5)

    if stats["closed_trades"] > 0:
        stats["avg_trade_pnl_eur"] = stats["realized_pnl_eur"] / stats["closed_trades"]
        stats["hit_rate_pct"] = (stats["win_trades"] / stats["closed_trades"]) * 100.0

    final_per_symbol = {}
    score_validation = []

    for sym, ps in per_symbol.items():
        trades = ps["trades"]
        if trades == 0:
            continue

        avg = ps["pnl"] / trades
        hit = (ps["wins"] / trades * 100.0) if trades > 0 else 0.0
        avg_score = sum(ps["scores"]) / len(ps["scores"]) if ps["scores"] else 0.0

        final_per_symbol[sym] = {
            "trades": trades,
            "pnl": ps["pnl"],
            "avg": avg,
            "hit": hit,
            "score": avg_score,
        }

        score_validation.append({
            "symbol": sym,
            "score": avg_score,
            "pnl": ps["pnl"],
            "trades": trades,
            "hit": hit,
        })

    stats["per_symbol"] = final_per_symbol
    stats["score_validation"] = score_validation

    return stats


def print_performance():
    stats = analyze_performance()

    if not stats:
        print("\nKeine Daten vorhanden.")
        return

    name_cache = {}

    print("\n==============================")
    print("SIMULATIONS-AUSWERTUNG")
    print("------------------------------")
    print(f"Trades: {stats['closed_trades']}")
    print(f"P/L: {stats['realized_pnl_eur']:.2f} EUR")
    print(f"Trefferquote: {stats['hit_rate_pct']:.2f}%")
    print("------------------------------")

    print("PERFORMANCE JE AKTIE:")

    ranked = sorted(
        stats["per_symbol"].items(),
        key=lambda x: x[1]["pnl"],
        reverse=True,
    )

    for sym, data in ranked[:10]:
        label = _format_symbol_with_name(sym, name_cache)

        print(
            f"{label}\n"
            f"  Score: {data['score']:.1f} | "
            f"P/L: {data['pnl']:.2f} EUR | "
            f"Ø: {data['avg']:.2f} EUR | "
            f"Treffer: {data['hit']:.1f}%"
        )

    print("\n------------------------------")
    print("SCORE VALIDIERUNG:")

    ranked_score = sorted(
        stats["score_validation"],
        key=lambda x: x["score"],
        reverse=True,
    )

    for item in ranked_score[:10]:
        label = _format_symbol_with_name(item["symbol"], name_cache)

        print(
            f"{label}\n"
            f"  Score: {item['score']:.1f} | "
            f"P/L: {item['pnl']:.2f} EUR | "
            f"Trades: {item['trades']} | "
            f"Treffer: {item['hit']:.1f}%"
        )

    print("\n==============================\n")
