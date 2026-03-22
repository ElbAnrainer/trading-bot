def print_summary_only(currency, closed_trades):
    total_pnl = sum(t["pnl"] for t in closed_trades)
    wins = sum(1 for t in closed_trades if t["pnl"] > 0)
    losses = sum(1 for t in closed_trades if t["pnl"] < 0)
    total = len(closed_trades)

    hit = (wins / total * 100) if total else 0

    print("\n==============================")
    print("GESAMT")
    print("------------------------------")
    print(f"Abgeschlossene Trades : {total}")
    print(f"Gewinntrades          : {wins}")
    print(f"Verlusttrades         : {losses}")
    print(f"Trefferquote          : {hit:.2f} %")
    print(f"Gesamt P/L            : {total_pnl:.2f} {currency}")
    print("==============================\n")


def print_ranking(results, currency):
    print("\n====================================================")
    print("RANKING DER BESTEN BACKTESTS")
    print("====================================================")

    for i, r in enumerate(results, 1):
        print(f"{i}. {r['symbol']} | {r['pnl']:.2f} {currency} ({r['pnl_pct']:.2f}%) | Trades: {r['trade_count']}")

    print("====================================================\n")


def print_recommendation(symbol, signal, price):
    print(f"{symbol}: {signal} @ {price:.2f}")


def print_portfolio(portfolio, currency):
    print("\n==============================")
    print("DEPOT")
    print("------------------------------")

    total = 0
    for s, p in portfolio.items():
        val = p["qty"] * p["price"]
        total += val
        print(f"{s}: {p['qty']} @ {p['price']:.2f} = {val:.2f}")

    print("------------------------------")
    print(f"Depotwert: {total:.2f} {currency}")
    print("==============================\n")


def print_closed_trades(symbol, currency, trades):
    if not trades:
        return

    print(f"\nDETAILS {symbol}")
    for t in trades:
        print(f"{t['buy_time']} → {t['sell_time']} | P/L: {t['pnl']:.2f}")
