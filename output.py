def print_human(symbol, name, wkn, signal, qty, price, summary):
    print("\n==============================")
    print(f"{name} ({symbol})")
    print(f"WKN: {wkn}")
    print("------------------------------")

    if signal == "BUY":
        print(f"👉 KAUFEN: {qty} Stück @ {price:.2f}")
    elif signal == "SELL":
        print("👉 VERKAUFEN")
    else:
        print("👉 HALTEN")

    print("------------------------------")
    print(f"Cash: {summary['cash']:.2f}")
    print(f"Bestand: {summary['position']}")
    print("==============================\n")


def print_technical(data):
    print("TECH:", data)


def print_closed_trades(name, symbol, wkn, currency, closed_trades):
    print("\n==============================")
    print("TRADE-AUSWERTUNG")
    print(f"{name} ({symbol})")
    print(f"WKN: {wkn}")
    print("==============================")

    if not closed_trades:
        print("Keine abgeschlossenen Trades vorhanden.\n")
        return

    total_pnl = 0.0
    wins = 0
    losses = 0

    for i, trade in enumerate(closed_trades, start=1):
        total_pnl += trade["pnl"]

        if trade["pnl"] > 0:
            wins += 1
        elif trade["pnl"] < 0:
            losses += 1

        print(f"\nTrade {i}")
        print("------------------------------")
        print(f"Kaufdatum      : {trade['buy_time']}")
        print(f"Kaufkurs       : {trade['buy_price']:.2f} {currency}")
        print(f"Stückzahl      : {trade['qty']}")
        print(f"Kaufsumme      : {trade['buy_total']:.2f} {currency}")
        print()
        print(f"Verkaufsdatum  : {trade['sell_time']}")
        print(f"Verkaufskurs   : {trade['sell_price']:.2f} {currency}")
        print(f"Verkaufssumme  : {trade['sell_total']:.2f} {currency}")
        print()
        print(f"Ergebnis       : {trade['pnl']:.2f} {currency}")
        print(f"Ergebnis in %  : {trade['pnl_pct']:.2f} %")

    total_trades = len(closed_trades)
    hit_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

    print("\n==============================")
    print("GESAMT")
    print("------------------------------")
    print(f"Abgeschlossene Trades : {total_trades}")
    print(f"Gewinntrades          : {wins}")
    print(f"Verlusttrades         : {losses}")
    print(f"Trefferquote          : {hit_rate:.2f} %")
    print(f"Gesamt P/L            : {total_pnl:.2f} {currency}")
    print("==============================\n")
