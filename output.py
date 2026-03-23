from config import BASE_CURRENCY

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def colorize(value, text):
    if value > 0:
        return f"{GREEN}{text}{RESET}"
    if value < 0:
        return f"{RED}{text}{RESET}"
    return text


def colorize_signal(signal):
    if signal == "BUY":
        return f"{GREEN}{signal}{RESET}"
    if signal == "SELL":
        return f"{RED}{signal}{RESET}"
    if signal == "WATCH":
        return f"{YELLOW}{signal}{RESET}"
    return signal


def print_summary_only(closed_trades, native_currency):
    total_pnl_eur = sum(t.get("pnl_eur", 0.0) for t in closed_trades)

    wins = sum(1 for t in closed_trades if t.get("pnl_eur", 0.0) > 0)
    losses = sum(1 for t in closed_trades if t.get("pnl_eur", 0.0) < 0)
    total = len(closed_trades)

    hit = (wins / total * 100) if total else 0.0
    pnl_str = colorize(total_pnl_eur, f"{total_pnl_eur:.2f} EUR")

    print("==============================")
    print("GESAMT (EUR)")
    print("------------------------------")
    print(f"Abgeschlossene Trades : {total}")
    print(f"Gewinntrades          : {wins}")
    print(f"Verlusttrades         : {losses}")
    print(f"Trefferquote          : {hit:.2f} %")
    print(f"Gesamt P/L            : {pnl_str}")
    print("==============================\n")


def print_ranking(results):
    print("\n====================================================")
    print("RANKING DER BESTEN BACKTESTS (EUR)")
    print("====================================================")

    for i, r in enumerate(results, 1):
        pnl = r["pnl_eur"]
        pnl_str = colorize(pnl, f"{pnl:.2f} EUR")

        print(
            f"{i}. {r['symbol']} | "
            f"{pnl_str} ({r['pnl_pct_eur']:.2f}%) | "
            f"Trades: {r['trade_count']}"
        )

    print("====================================================\n")


def print_recommendation(symbol, signal, price_eur, price_native, native_currency):
    signal_str = colorize_signal(signal)

    if native_currency == BASE_CURRENCY:
        print(f"{symbol}: {signal_str} @ {price_eur:.2f} EUR")
    else:
        print(
            f"{symbol}: {signal_str} @ "
            f"{price_eur:.2f} EUR "
            f"(Handel: {price_native:.2f} {native_currency})"
        )


def print_portfolio(portfolio):
    print("\n==============================")
    print("DEPOT (EUR)")
    print("------------------------------")

    total = 0.0

    if not portfolio:
        print("Keine Positionen im virtuellen Depot.")

    for symbol, pos in portfolio.items():
        value = pos["qty"] * pos["price_eur"]
        total += value
        value_str = colorize(value, f"{value:.2f} EUR")

        if pos["native_currency"] == BASE_CURRENCY:
            print(f"{symbol}: {pos['qty']} Stück | Wert {value_str}")
        else:
            native_value = pos["qty"] * pos["price_native"]
            print(
                f"{symbol}: {pos['qty']} Stück | "
                f"Wert {value_str} | "
                f"{native_value:.2f} {pos['native_currency']}"
            )

    print("------------------------------")
    print(f"Depotwert: {colorize(total, f'{total:.2f} EUR')}")
    print("==============================\n")


def print_future_candidates(candidates):
    print("\n====================================================")
    print("TOP-KANDIDATEN FÜR DIE ZUKUNFT")
    print("====================================================")

    if not candidates:
        print("Keine Kandidaten gefunden.")
        print("====================================================\n")
        return

    for i, c in enumerate(candidates, 1):
        reasons = ", ".join(c.get("reasons", [])) if c.get("reasons") else "keine klare Begründung"

        print(
            f"{i}. {c['symbol']} | "
            f"{colorize_signal(c['future_signal'])} | "
            f"Score: {c['score']:.2f} | "
            f"Stärke: {c['strength']} | "
            f"Risiko: {c['risk']}"
        )
        print(f"   Grund: {reasons}")

    print("====================================================\n")


def print_financial_overview(start, end, pnl, currency, pnl_native):
    print("\n==============================")
    print("FINANZÜBERSICHT")
    print("------------------------------")
    print(f"Start     : {start:.2f} EUR")
    print(f"Stand     : {end:.2f} EUR")
    print(f"Differenz : {colorize(pnl, f'{pnl:.2f} EUR')}")
    if currency != BASE_CURRENCY:
        print(f"Info      : {pnl_native:.2f} {currency}")
    print("==============================\n")


def print_equity_curve_terminal(symbol, curve):
    if not curve:
        return

    values = [p["equity_eur"] for p in curve]

    blocks = "▁▂▃▄▅▆▇█"
    min_v = min(values)
    max_v = max(values)

    if max_v == min_v:
        line = "─" * len(values)
    else:
        line = ""
        for v in values:
            idx = int((v - min_v) / (max_v - min_v) * (len(blocks) - 1))
            line += blocks[idx]

    print("\n==============================")
    print(f"DEPOTWERT-KURVE {symbol}")
    print("------------------------------")
    print(line)
    print(f"Start: {values[0]:.2f} | Ende: {values[-1]:.2f}")
    print("==============================\n")


def print_closed_trades(symbol, name, isin, wkn, trades, currency):
    if not trades:
        return

    print(f"\nDETAILS {symbol}")
    print("------------------------------")
    print(f"{name}")
    print(f"ISIN: {isin} | WKN: {wkn} | Währung: {currency}")
    print("------------------------------")

    for t in trades:
        pnl_eur = t.get("pnl_eur", 0.0)
        pnl_str = colorize(pnl_eur, f"{pnl_eur:.2f} EUR")
        print(f"{t['buy_time']} -> {t['sell_time']} | {pnl_str}")


def print_diagnostics(info):
    print("\n------------------------------")
    print(f"DIAGNOSE {info['symbol']}")
    print("------------------------------")

    def yn(v):
        return "JA" if v else "NEIN"

    print(f"Trend                : {yn(info.get('trend_ok'))}")
    print(f"Breakout             : {yn(info.get('breakout_ok'))}")
    print(f"Momentum             : {yn(info.get('momentum_ok'))}")
    print(f"Volatilität          : {yn(info.get('volatility_ok'))}")
    print(f"Relative Stärke      : {yn(info.get('relative_strength_ok'))}")

    rs = info.get("relative_strength_pct")
    if rs is not None:
        print(f"RS vs Markt          : {rs:.2f}%")

    print(f"Fundamental Score    : {info.get('fundamental_score')}")
    print(f"Score                : {info.get('score'):.2f}")
    print(f"Aktuell              : {info.get('current_signal')}")
    print(f"Zukunft              : {info.get('future_signal')}")
    print("------------------------------\n")


def print_buy_overview(candidates):
    print("\n====================================================")
    print("KAUFEMPFEHLUNGEN (ÜBERSICHT)")
    print("====================================================")

    filtered = [c for c in candidates if c["future_signal"] in ("BUY", "WATCH")]

    if not filtered:
        print("Keine BUY/WATCH Kandidaten gefunden.")
        print("====================================================\n")
        return

    for i, c in enumerate(filtered, 1):
        print(
            f"{i}. {c['symbol']} | "
            f"{colorize_signal(c['future_signal'])} | "
            f"Score: {c['score']:.2f} | "
            f"Stärke: {c['strength']} | "
            f"Risiko: {c['risk']}"
        )

    print("====================================================\n")


def print_buy_blockers_summary(blockers):
    print("\n====================================================")
    print("WARUM GIBT ES KAUM BUY-SIGNALE?")
    print("====================================================")

    if not blockers:
        print("Keine Blocker erkannt.")
        print("====================================================\n")
        return

    sorted_items = sorted(blockers.items(), key=lambda x: x[1], reverse=True)

    for i, (name, count) in enumerate(sorted_items, 1):
        if count <= 0:
            continue
        print(f"{i}. {name:<24}: {count} Aktien")

    print("====================================================\n")


def print_runtime(seconds):
    print("\n==============================")
    print("LAUFZEIT")
    print("------------------------------")
    print(f"{seconds:.2f} Sekunden")
    print("==============================\n")
