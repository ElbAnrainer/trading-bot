import time
from terminal_ui import clear, colorize, get_width

COLS = [
    ("SYM", 6),
    ("BONUS", 10),
    ("TREFFER", 10),
    ("Ø P/L", 14),
    ("TRADES", 8),
]


def _header():
    return "".join(f"{name:<{w}}" if i == 0 else f"{name:>{w}}" for i, (name, w) in enumerate(COLS))


def _row(r):
    sym = f"{r['symbol']:<6}"

    bonus_val = f"{r['bonus']:+.2f}"
    bonus = colorize(r["bonus"], f"{bonus_val:>10}")

    hit = f"{r['hit_rate']:>9.1f}%"

    pnl_val = f"{r['avg_pnl']:,.2f}"
    pnl = colorize(r["avg_pnl"], f"{pnl_val:>14}")

    trades = f"{r['trades']:>8}"

    return f"{sym}{bonus}{hit}{pnl}{trades}"


def render_live_table(ranking, title="LIVE TRADING TABLE"):
    clear()

    width = get_width()

    print("=" * width)
    print(title.center(width))
    print("-" * width)

    header = _header()
    print(header)
    print("-" * len(header))

    for r in ranking[:10]:
        print(_row(r))

    print("=" * width)


# =========================================================
# LIVE LOOP (für echtes Terminal)
# =========================================================
def run_live_table(get_data_func, interval=1.0):
    """
    get_data_func muss liefern:
    {
        "ranking": [...]
    }
    """

    while True:
        data = get_data_func()
        ranking = data.get("ranking", [])

        render_live_table(ranking)

        time.sleep(interval)
