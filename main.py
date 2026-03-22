from config import *
from broker import Broker
from data_loader import load_data
from strategy import add_signals, normalize_signal, compute_qty
from output import print_human, print_technical


def main():
    df = load_data(SYMBOL, PERIOD, INTERVAL)
    df = add_signals(df)

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

    print_technical({
        "signal": signal,
        "qty": qty,
        "price": price,
        "summary": summary
    })


if __name__ == "__main__":
    main()
