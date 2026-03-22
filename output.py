from config import BASE_CURRENCY

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def colorize(value, text):
    if value > 0:
        return f"{GREEN}{text}{RESET}"
    if value < 0:
        return f"{RED}{text}{RESET}"
    return text


# ---------------------------
# FINANZÜBERSICHT
# ---------------------------
def print_financial_overview(initial_cash_eur, current_equity_eur, pnl_eur, native_currency, pnl_native):
    pnl_eur_str = colorize(pnl_eur, f"{pnl_eur:.2f} EUR")

    print("\n==============================")
    print("FINANZÜBERSICHT (Basis: EUR)")
    print("------------------------------")
    print(f"Start          : {initial_cash_eur:.2f} EUR")
    print(f"Stand          : {current_equity_eur:.2f} EUR")
    print(f"Differenz      : {pnl_eur_str}")

    if native_currency != BASE_CURRENCY:
        print(
            f"Handelsergebnis ({native_currency}): "
            f"{colorize(pnl_native, f'{pnl_native:.2f} {native_currency}')}"
        )

    print("==============================\n")


# ---------------------------
# GESAMT
# ---------------------------
def print_summary_only(closed_trades, native_currency):
    total_pnl_eur = sum(t.get("pnl_eur", 0.0) for t in closed_trades)
    total_pnl_native = sum(t.get("pnl_native", 0.0) for t in closed_trades)

    wins = sum(1 for t in closed_trades if t.get("pnl_eur", 0.0) > 0)
    losses = sum(1 for t in closed_trades if t.get("pnl_eur", 0.0) < 0)
    total = len(closed_trades)

    hit = (wins / total * 100) if total else 0.0

    pnl_eur_str = colorize(total_pnl_eur, f"{total_pnl_eur:.2f} EUR")

    print("==============================")
    print("GESAMT (EUR)")
    print("------------------------------")
    print(f"Abgeschlossene Trades : {total}")
    print(f"Gewinntrades          : {wins}")
    print(f"Verlusttrades         : {losses}")
    print(f"Trefferquote          : {hit:.2f} %")
    print(f"Gesamt P/L            : {pnl_eur_str}")

    if native_currency != BASE_CURRENCY:
        print(
            f"Handelsergebnis ({native_currency}): "
            f"{colorize(total_pnl_native, f'{total_pnl_native:.2f} {native_currency}')}"
        )

    print("==============================\n")


# ---------------------------
# RANKING (NEU: FX-ANALYSE)
# ---------------------------
def print_ranking(results):
    print("\n====================================================")
    print("RANKING DER BESTEN BACKTESTS (EUR + FX ANALYSE)")
    print("====================================================")

    for i, r in enumerate(results, 1):
        pnl_eur = r["pnl_eur"]
        pnl_native = r["pnl_native"]
        currency = r["native_currency"]

        pnl_eur_str = colorize(pnl_eur, f"{pnl_eur:.2f} EUR")

        print(
            f"{i}. {r['symbol']} | "
            f"{pnl_eur_str} "
            f"({r['pnl_pct_eur']:.2f}%) | "
            f"Trades: {r['trade_count']}"
        )

        if currency != BASE_CURRENCY:
            fx_effect = pnl_eur - (pnl_native * 1.0)  # rein zur Anzeige

            print(
                f"   Aktie ({currency}): "
                f"{colorize(pnl_native, f'{pnl_native:.2f} {currency}')}"
            )
            print(
                f"   FX-Effekt       : "
                f"{colorize(fx_effect, f'{fx_effect:.2f} EUR')}"
            )

    print("====================================================\n")


# ---------------------------
# EMPFEHLUNG
# ---------------------------
def print_recommendation(symbol, signal, price_eur, price_native, native_currency):
    color = GREEN if signal == "BUY" else RED if signal == "SELL" else RESET

    if native_currency == BASE_CURRENCY:
        print(f"{symbol}: {color}{signal}{RESET} @ {price_eur:.2f} EUR")
    else:
        print(
            f"{symbol}: {color}{signal}{RESET} @ "
            f"{price_eur:.2f} EUR "
            f"(Handel in {native_currency}: {price_native:.2f})"
        )


# ---------------------------
# DEPOT
# ---------------------------
def print_portfolio(portfolio):
    print("\n==============================")
    print("DEPOT (EUR)")
    print("------------------------------")

    total_eur = 0.0

    if not portfolio:
        print("Keine Positionen im virtuellen Depot.")

    for symbol, pos in portfolio.items():
        value_eur = pos["qty"] * pos["price_eur"]
        total_eur += value_eur

        extra = ""
        if pos["native_currency"] != BASE_CURRENCY:
            value_native = pos["qty"] * pos["price_native"]
            extra = f" | {value_native:.2f} {pos['native_currency']}"

        print(
            f"{symbol}: {pos['qty']} Stück | "
            f"Wert {colorize(value_eur, f'{value_eur:.2f} EUR')}"
            f"{extra}"
        )

    print("------------------------------")
    print(f"Depotwert: {colorize(total_eur, f'{total_eur:.2f} EUR')}")
    print("==============================\n")


# ---------------------------
# TRADES
# ---------------------------
def print_closed_trades(symbol, company_name, isin, wkn, trades, native_currency):
    if not trades:
        return

    print(f"\nDETAILS {symbol}")
    print("------------------------------")
    print(f"Name            : {company_name}")
    print(f"ISIN            : {isin}")
    print(f"WKN             : {wkn}")
    print(f"Handelswährung  : {native_currency}")
    print("------------------------------")

    for t in trades:
        pnl_eur = t["pnl_eur"]
        pnl_native = t["pnl_native"]

        print(f"Kaufdatum       : {t['buy_time']}")
        print(f"Verkaufsdatum   : {t['sell_time']}")
        print(f"Ergebnis (EUR)  : {colorize(pnl_eur, f'{pnl_eur:.2f} EUR')}")

        if native_currency != BASE_CURRENCY:
            fx_effect = pnl_eur - pnl_native
            print(f"Aktie ({native_currency}): {colorize(pnl_native, f'{pnl_native:.2f} {native_currency}')}")
            print(f"FX-Effekt       : {colorize(fx_effect, f'{fx_effect:.2f} EUR')}")

        print(f"Ergebnis in %   : {t['pnl_pct_eur']:.2f} %")
        print("------------------------------")


# ---------------------------
# KURVE
# ---------------------------
def print_equity_curve_terminal(symbol, equity_curve_eur):
    if not equity_curve_eur or len(equity_curve_eur) < 2:
        return

    values = [p["equity_eur"] for p in equity_curve_eur]
    labels = [p["time"] for p in equity_curve_eur]

    blocks = "▁▂▃▄▅▆▇█"
    min_val = min(values)
    max_val = max(values)

    sparkline = ""
    for v in values:
        idx = int((v - min_val) / (max_val - min_val + 1e-9) * (len(blocks) - 1))
        sparkline += blocks[idx]

    change = values[-1] - values[0]
    sparkline = colorize(change, sparkline)

    print("\n==============================")
    print(f"DEPOTWERT-KURVE {symbol} (EUR)")
    print("------------------------------")
    print(sparkline)
    print(
        f"Start: {values[0]:.2f} EUR | "
        f"Tief: {min_val:.2f} EUR | "
        f"Hoch: {max_val:.2f} EUR | "
        f"Ende: {values[-1]:.2f} EUR"
    )
    print(f"Von: {labels[0]}")
    print(f"Bis: {labels[-1]}")
    print("==============================\n")
