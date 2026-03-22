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
