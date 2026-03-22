from config import SYMBOL, NAME, WKN, CURRENCY, PERIOD, INTERVAL, INITIAL_CASH
from broker import Broker
from data_loader import load_data
from strategy import add_signals, normalize_signal, compute_qty
from output import print_human, print_technical, print_closed_trades


def ask_user_for_period():
    print("\nWelchen Zeitraum möchtest du testen?")
    print("Beispiele:")
    print("  5d   = 5 Tage")
    print("  1mo  = 1 Monat")
    print("  3mo  = 3 Monate")
    print("  6mo  = 6 Monate")
    print("  1y   = 1 Jahr")
    print("  2y   = 2 Jahre")
    print("  3y   = 3 Jahre")
    print()

    period = input("Zeitraum eingeben (Enter = Standard aus config): ").strip()

    if period == "":
        return PERIOD

    return period


def choose_interval(period: str) -> str:
    if period in ("1d", "5d", "1mo"):
        return "5m"
    if period in ("3mo", "6mo"):
        return "1h"
    if period in ("1y", "2y", "3y", "5y", "max"):
        return "1d"

    return INTERVAL


def main(period):
    interval = choose_interval(period)

    df = load_data(SYMBOL, period, interval)
    df = add_signals(df)

    if df.empty:
        print("\nKeine Kursdaten gefunden.")
        print(f"Symbol   : {SYMBOL}")
        print(f"Zeitraum : {period}")
        print(f"Intervall: {interval}")
        return

    last = df.iloc[-1]
    price = float(last["Close"])
    signal = normalize_signal(int(last["signal"]))

    broker = Broker(cash=INITIAL_CASH)
    qty = compute_qty(broker.cash, price)

    if signal == "BUY":
        broker.buy(price, qty, "now")
    elif signal == "SELL":
        broker.sell(price, "now")

    summary = broker.summary(price)

    print_human(SYMBOL, NAME, WKN, signal, qty, price, summary)

    print_technical(
        {
            "symbol": SYMBOL,
            "signal": signal,
            "qty": qty,
            "price": price,
            "summary": summary,
            "period": period,
            "interval": interval,
        }
    )


def run_backtest(period):
    interval = choose_interval(period)

    df = load_data(SYMBOL, period, interval)
    df = add_signals(df).dropna().copy()

    if df.empty:
        print("\n==============================")
        print("BACKTEST-ERGEBNIS")
        print(f"{NAME} ({SYMBOL})")
        print(f"WKN: {WKN}")
        print("------------------------------")
        print("Keine Daten für den gewählten Zeitraum vorhanden.")
        print(f"Zeitraum: {period}")
        print(f"Intervall: {interval}")
        print("==============================\n")
        return

    broker = Broker(cash=INITIAL_CASH)
    prev_signal = 0

    for idx, row in df.iterrows():
        price = float(row["Close"])
        signal_value = int(row["signal"])
        qty = compute_qty(broker.cash, price)
        ts = str(idx)

        if signal_value != prev_signal:
            if signal_value == 1 and broker.position == 0:
                broker.buy(price, qty, ts)
            elif signal_value == -1 and broker.position > 0:
                broker.sell(price, ts)

        prev_signal = signal_value

    last_price = float(df.iloc[-1]["Close"])
    summary = broker.summary(last_price)
    pnl = summary["equity"] - INITIAL_CASH
    pnl_pct = (pnl / INITIAL_CASH) * 100

    print("\n==============================")
    print("BACKTEST-ERGEBNIS")
    print(f"{NAME} ({SYMBOL})")
    print(f"WKN: {WKN}")
    print("------------------------------")
    print(f"Zeitraum: {period}")
    print(f"Intervall: {interval}")
    print(f"Cash: {summary['cash']:.2f} {CURRENCY}")
    print(f"Bestand: {summary['position']}")
    print(f"Ø Einstieg: {summary['avg_entry']:.2f} {CURRENCY}")
    print(f"Depotwert: {summary['equity']:.2f} {CURRENCY}")
    print(f"Ergebnis: {pnl:.2f} {CURRENCY} ({pnl_pct:.2f}%)")
    print(f"Trades: {len(broker.trades)}")
    print("==============================\n")

    print_closed_trades(NAME, SYMBOL, WKN, CURRENCY, broker.closed_trades)

    if broker.trades:
        print("LETZTE ROH-TRADES")
        for trade in broker.trades[-5:]:
            print(trade)
    else:
        print("Keine Trades im Backtest.")


if __name__ == "__main__":
    selected_period = ask_user_for_period()
    main(selected_period)
    print()
    run_backtest(selected_period)
