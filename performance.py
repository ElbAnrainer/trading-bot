import csv
import os
from collections import defaultdict
from statistics import mean

from terminal_ui import box, colorize
from live_table import run_live_table

try:
    from learning import get_score, update_score
except:
    def get_score(x): return None
    def update_score(x, y): return y

try:
    from portfolio import build_portfolio
except:
    def build_portfolio(ranking, top_n=5, capital=1000):
        return []


JOURNAL_PATHS = [
    "reports/trading_journal.csv",
    "trading_journal.csv",
]


# =========================================================
# HELPERS
# =========================================================
def _to_float(v, d=0.0):
    try:
        return float(v)
    except:
        return d


def _load():
    for p in JOURNAL_PATHS:
        if os.path.exists(p):
            with open(p, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
                break
    else:
        return [], []

    trades = []
    for r in rows:
        if str(r.get("closed_trade", "")).lower() != "true":
            continue

        trades.append({
            "symbol": r.get("symbol", ""),
            "company": r.get("company", ""),
            "isin": r.get("isin", "-"),
            "wkn": r.get("wkn", "-"),
            "pnl": _to_float(r.get("realized_pnl_eur", 0)),
            "score": _to_float(r.get("score", 0)),
        })

    return trades, rows


# =========================================================
# CORE
# =========================================================
def analyze_performance():
    trades, rows = _load()

    stats = defaultdict(lambda: {
        "company": "",
        "isin": "-",
        "wkn": "-",
        "trades": 0,
        "wins": 0,
        "pnl": 0.0,
        "scores": [],
    })

    for t in trades:
        s = stats[t["symbol"]]
        s["company"] = t["company"]
        s["isin"] = t.get("isin", "-")
        s["wkn"] = t.get("wkn", "-")
        s["trades"] += 1
        s["pnl"] += t["pnl"]
        s["scores"].append(t["score"])

        if t["pnl"] > 0:
            s["wins"] += 1

    ranking = []

    for sym, s in stats.items():
        if s["trades"] == 0:
            continue

        hit = s["wins"] / s["trades"]
        avg_pnl = s["pnl"] / s["trades"]

        perf = s["pnl"] * 0.6 + hit * 100 * 0.3 + s["trades"] * 0.1

        learned = update_score(sym, perf)
        stored = get_score(sym)

        ranking.append({
            "symbol": sym,
            "company": s["company"],
            "isin": s["isin"],
            "wkn": s["wkn"],
            "trades": s["trades"],
            "hit_rate": hit * 100,
            "avg_pnl": avg_pnl,
            "bonus": perf / 100,
            "learned_score": stored if stored else learned,
        })

    ranking.sort(key=lambda x: x["learned_score"], reverse=True)

    portfolio = build_portfolio(ranking)

    top_symbols = [
        {
            "symbol": item["symbol"],
            "company": item.get("company", item["symbol"]),
            "isin": item.get("isin", "-"),
            "wkn": item.get("wkn", "-"),
            "count": item["trades"],
        }
        for item in ranking[:5]
    ]

    return {
        "ranking": ranking,
        "portfolio": portfolio,
        "top_symbols": top_symbols,
        "total_entries": len(rows),
        "closed_trades": len(trades),
        "winning_trades": sum(1 for t in trades if t["pnl"] > 0),
        "losing_trades": sum(1 for t in trades if t["pnl"] < 0),
        "hit_rate": (sum(1 for t in trades if t["pnl"] > 0) / len(trades) * 100.0) if trades else 0.0,
        "realized_pnl": sum(t["pnl"] for t in trades),
        "avg_trade_pnl": (sum(t["pnl"] for t in trades) / len(trades)) if trades else 0.0,
    }


# =========================================================
# FORMAT (FIXED ALIGNMENT)
# =========================================================
def _format_header():
    return f"{'SYM':<6}{'ISIN':<14}{'WKN':<8}{'BONUS':>10}{'TREFFER':>10}{'Ø P/L':>14}{'TRADES':>8}"


def _format_row(r):
    sym = f"{r['symbol']:<6}"
    isin = f"{r.get('isin', '-'):<14}"[:14]
    wkn = f"{r.get('wkn', '-'):<8}"[:8]

    bonus = colorize(r["bonus"], f"{r['bonus']:+10.2f}")
    hit = f"{r['hit_rate']:>9.1f}%"
    pnl = colorize(r["avg_pnl"], f"{r['avg_pnl']:>14,.2f}")
    trades = f"{r['trades']:>8}"

    return f"{sym}{isin}{wkn}{bonus}{hit}{pnl}{trades}"


# =========================================================
# PRINT (STATIC)
# =========================================================
def print_performance():
    data = analyze_performance()

    lines = []
    header = _format_header()

    lines.append(header)
    lines.append("-" * len(header))

    for r in data["ranking"][:10]:
        lines.append(_format_row(r))

    box("SELBSTLERNENDER SCORE", lines)

    # Portfolio
    p_lines = []
    header = f"{'SYM':<6}{'ISIN':<14}{'WKN':<8}{'GEWICHT':>10}{'KAPITAL':>14}"
    p_lines.append(header)
    p_lines.append("-" * len(header))

    for p in data["portfolio"]:
        p_lines.append(
            f"{p['symbol']:<6}"
            f"{str(p.get('isin', '-'))[:14]:<14}"
            f"{str(p.get('wkn', '-'))[:8]:<8}"
            f"{p['weight']:>10.2f}"
            f"{p['capital']:>14.2f} EUR"
        )

    box("PORTFOLIO", p_lines)

    return data


# =========================================================
# 🔥 LIVE MODE
# =========================================================
def run_live():
    def get_data():
        return analyze_performance()

    run_live_table(get_data, interval=1.0)


if __name__ == "__main__":
    print_performance()
