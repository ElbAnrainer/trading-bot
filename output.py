from config import BASE_CURRENCY, NATIVE_CURRENCY

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
def print_financial_overview(initial_cash_usd, initial_cash_eur, current_equity_usd, current_equity_eur):
    pnl_usd = current_equity_usd - initial_cash_usd
    pnl_eur = current_equity_eur - initial_cash_eur

    pnl_eur_str = colorize(pnl_eur, f"{pnl_eur:.2f} EUR")
    pnl_usd_str = colorize(pnl_usd, f"{pnl_usd:.2f} USD")

    print("\n==============================")
    print("FINANZÜBERSICHT (Basis: EUR)")
    print("------------------------------")
    print(f"Start          : {initial_cash_eur:.2f} EUR")
    print(f"Stand          : {current_equity_eur:.2f} EUR")
    print(f"Differenz      : {pnl_eur_str}")
    print(f"(Info USD      : {pnl_usd_str})")
    print("==============================\n")


# ---------------------------
# GESAMT
# ---------------------------
def print_summary_only(closed_trades):
    total_pnl_eur = sum(t.get("pnl_eur", 0.0) for t in closed_trades)
    total_pnl_usd = sum(t.get("pnl", 0.0) for t in closed_trades)

    wins = sum(1 for t in closed_trades if t.get("pnl_eur", 0.0) > 0)
    losses = sum(1 for t in closed_trades if t.get("pnl_eur", 0.0) < 0)
    total = len(closed_trades)

    hit = (wins / total * 100) if total else 0.0

    pnl_eur_str = colorize(total_pnl_eur, f"{total_pnl_eur:.2f} EUR")
    pnl_usd_str = colorize(total_pnl_usd, f"{total_pnl_usd:.2f} USD")

    print("==============================")
    print("GESAMT (EUR)")
    print("------------------------------")
    print(f"Abgeschlossene Trades : {total}")
    print(f"Gewinntrades          : {wins}")
    print(f"Verlusttrades         : {losses}")
    print(f"Trefferquote          : {hit:.2f} %")
    print(f"Gesamt P/L            : {pnl_eur_str}")
    print(f"(Info USD             : {pnl_usd_str})")
    print("==============================\n")


# ---------------------------
# RANKING
# ---------------------------
def print_ranking(results):
    print("\n====================================================")
    print("RANKING DER BESTEN BACKTESTS (EUR)")
    print("====================================================")

    for i, r in enumerate(results, 1):
        pnl_eur_str = colorize(r["pnl_eur"], f"{r['pnl_eur']:.2f} EUR")
        pnl_usd_str = colorize(r["pnl"], f"{r['pnl']:.2f} USD")

        print(
            f"{i}. {r['symbol']} | "
            f"{pnl_eur_str} "
            f"({r['pnl_pct_eur']:.2f}%) | "
            f"Trades: {r['trade_count']} "
            f"| USD: {pnl_usd_str}"
        )

    print("====================================================\n")


# ---------------------------
# EMPFEHLUNG
# ---------------------------
def print_recommendation(symbol, signal, price_eur, price_usd):
    color = GREEN if signal == "BUY" else RED if signal == "SELL" else RESET

    print(
        f"{symbol}: {color}{signal}{RESET} @ "
        f"{price_eur:.2f} EUR "
        f"(Handel in USD: {price_usd:.2f})"
    )


# ---------------------------
# DEPOT
# ---------------------------
def print_portfolio(portfolio):
    print("\n==============================")
    print("DEPOT (EUR)")
    print("------------------------------")

    total_eur = 0.0
    total_usd = 0.0

    if not portfolio:
        print("Keine Positionen im virtuellen Depot.")

    for symbol, pos in portfolio.items():
        value_eur = pos["qty"] * pos["price_eur"]
        value_usd = pos["qty"] * pos["price_usd"]

        total_eur += value_eur
        total_usd += value_usd

        val_eur_str = colorize(value_eur, f"{value_eur:.2f} EUR")
        val_usd_str = colorize(value_usd, f"{value_usd:.2f} USD")

        print(
            f"{symbol}: {pos['qty']} Stück | "
            f"Wert {val_eur_str} "
            f"(USD: {val_usd_str})"
        )

    total_eur_str = colorize(total_eur, f"{total_eur:.2f} EUR")
    total_usd_str = colorize(total_usd, f"{total_usd:.2f} USD")

    print("------------------------------")
    print(f"Depotwert: {total_eur_str}")
    print(f"(USD Info: {total_usd_str})")
    print("==============================\n")


# ---------------------------
# TRADES
# ---------------------------
def print_closed_trades(symbol, company_name, isin, wkn, trades):
    if not trades:
        return

    print(f"\nDETAILS {symbol}")
    print("------------------------------")
    print(f"Name            : {company_name}")
    print(f"ISIN            : {isin}")
    print(f"WKN             : {wkn}")
    print("------------------------------")

    for t in trades:
        pnl_eur_str = colorize(t["pnl_eur"], f"{t['pnl_eur']:.2f} EUR")
        pnl_usd_str = colorize(t["pnl"], f"{t['pnl']:.2f} USD")

        print(f"Kaufdatum       : {t['buy_time']}")
        print(f"Verkaufsdatum   : {t['sell_time']}")
        print(f"Ergebnis        : {pnl_eur_str}")
        print(f"(USD            : {pnl_usd_str})")
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
