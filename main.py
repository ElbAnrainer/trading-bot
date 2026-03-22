import sys

from config import *
from broker import Broker
from data_loader import load_data
from strategy import *
from output import *


def parse_args():
    return (
        "-l" in sys.argv,
        int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else DEFAULT_TOP_N,
        float(sys.argv[sys.argv.index("--min-volume") + 1]) if "--min-volume" in sys.argv else DEFAULT_MIN_VOLUME
    )


def choose_interval(p):
    if p in ("1d", "5d", "1mo"):
        return "5m"
    if p in ("3mo", "6mo"):
        return "1h"
    return "1d"


def ask():
    p = input("Zeitraum: ").strip()
    return p if p else PERIOD


def get_signal(symbol, period, interval):
    df = load_data(symbol, period, interval)
    df = add_signals(df)

    if df.empty:
        return None, None

    last = df.iloc[-1]
    return normalize_signal(int(last["signal"])), float(last["Close"])


def backtest(symbol, period, interval):
    df = load_data(symbol, period, interval)
    df = add_signals(df).dropna()

    if df.empty:
        return None

    broker = Broker(INITIAL_CASH)
    prev = 0

    for i, r in df.iterrows():
        price = float(r["Close"])
        sig = int(r["signal"])
        qty = compute_qty(broker.cash, price)

        if sig != prev:
            if sig == 1 and broker.position == 0:
                broker.buy(price, qty, str(i))
            elif sig == -1 and broker.position > 0:
                broker.sell(price, str(i))

        prev = sig

    last = float(df.iloc[-1]["Close"])
    s = broker.summary(last)

    pnl = s["equity"] - INITIAL_CASH
    pnl_pct = pnl / INITIAL_CASH * 100

    return {
        "symbol": symbol,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "trade_count": len(s["closed_trades"]),
        "closed_trades": s["closed_trades"],
        "last_price": last,
    }


if __name__ == "__main__":
    long, top, min_vol = parse_args()
    period = ask()
    interval = choose_interval(period)

    results = []
    portfolio = {}

    for s in SYMBOLS[:top]:
        signal, price = get_signal(s, period, interval)
        if signal:
            print_recommendation(s, signal, price)

        r = backtest(s, period, interval)
        if not r:
            continue

        print_summary_only(CURRENCY, r["closed_trades"])

        if long:
            print_closed_trades(s, CURRENCY, r["closed_trades"])

        if signal == "BUY":
            portfolio[s] = {"qty": 10, "price": price}
        elif signal == "SELL" and s in portfolio:
            del portfolio[s]

        results.append(r)

    results.sort(key=lambda x: x["pnl"], reverse=True)

    print_ranking(results, CURRENCY)
    print_portfolio(portfolio, CURRENCY)
