from config import BASE_CURRENCY


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

PRO_MODE = False
BEGINNER_MODE = False


def set_pro_mode(enabled):
    global PRO_MODE
    PRO_MODE = bool(enabled)


def set_beginner_mode(enabled):
    global BEGINNER_MODE
    BEGINNER_MODE = bool(enabled)


def _style(text, *styles):
    if not PRO_MODE or not styles:
        return text
    return "".join(styles) + str(text) + RESET


def colorize(value, text):
    if value > 0:
        return _style(text, GREEN)
    if value < 0:
        return _style(text, RED)
    return text


def colorize_signal(signal):
    if signal == "BUY":
        return _style(signal, GREEN, BOLD)
    if signal == "SELL":
        return _style(signal, RED, BOLD)
    if signal == "WATCH":
        return _style(signal, YELLOW, BOLD)
    if signal == "HOLD":
        return _style(signal, CYAN) if PRO_MODE else signal
    return signal


def _headline(text):
    return _style(text, BOLD) if PRO_MODE else text


def _warning_line(text):
    if PRO_MODE:
        return _style(f"⚠ {text}", YELLOW, BOLD)
    return text


def print_simulation_notice():
    print("\n==============================")
    print(_headline("SIMULATIONSHINWEIS"))
    print("------------------------------")
    print("Dieses System arbeitet nur mit Simulationsdaten.")
    print("Es werden keine echten Orders ausgeführt.")
    print("Es besteht keine Broker-Anbindung.")
    print(_warning_line("Keine Anlageberatung."))
    print("==============================\n")


def print_summary_only(closed_trades, native_currency):
    total_pnl_eur = sum(t.get("pnl_eur", 0.0) for t in closed_trades)

    wins = sum(1 for t in closed_trades if t.get("pnl_eur", 0.0) > 0)
    losses = sum(1 for t in closed_trades if t.get("pnl_eur", 0.0) < 0)
    total = len(closed_trades)

    avg_trade = (total_pnl_eur / total) if total else 0.0
    hit = (wins / total * 100) if total else 0.0
    pnl_str = colorize(total_pnl_eur, f"{total_pnl_eur:.2f} EUR")
    avg_str = colorize(avg_trade, f"{avg_trade:.2f} EUR")

    print("==============================")
    print(_headline("SIMULATIONSERGEBNIS (EUR)"))
    print("------------------------------")
    print(f"Abgeschlossene Trades : {total}")
    print(f"Gewinntrades          : {wins}")
    print(f"Verlusttrades         : {losses}")
    print(f"Trefferquote          : {hit:.2f} %")
    print(f"Ø Trade P/L           : {avg_str}")
    print(f"Gesamt P/L            : {pnl_str}")
    if PRO_MODE and hit < 45 and total >= 5:
        print(_warning_line("Trefferquote ist schwach."))
    print("==============================\n")


def print_ranking(results):
    print("\n====================================================")
    print(_headline("RANKING DER BESTEN BACKTESTS (EUR)"))
    print("====================================================")

    if not results:
        print("Keine Backtest-Ergebnisse vorhanden.")
        print("====================================================\n")
        return

    for i, r in enumerate(results, 1):
        pnl = r["pnl_eur"]
        pnl_str = colorize(pnl, f"{pnl:.2f} EUR")
        company = r.get("company_name", r["symbol"])
        signal = r.get("signal")
        signal_text = f" | {colorize_signal(signal)}" if signal else ""

        prefix = "★ " if PRO_MODE and i == 1 else ""
        print(
            f"{prefix}{i}. {r['symbol']} ({company}) | "
            f"{pnl_str} ({r['pnl_pct_eur']:.2f}%) | "
            f"Trades: {r['trade_count']}{signal_text}"
        )

    print("====================================================\n")


def print_recommendation(symbol, signal, price_eur, price_native, native_currency):
    signal_str = colorize_signal(signal)

    if native_currency == BASE_CURRENCY:
        line = f"{symbol}: {signal_str} @ {price_eur:.2f} EUR"
    else:
        line = (
            f"{symbol}: {signal_str} @ "
            f"{price_eur:.2f} EUR "
            f"(Handel: {price_native:.2f} {native_currency})"
        )

    if PRO_MODE and signal == "SELL":
        line = _warning_line(line)

    print(line)


def print_portfolio(portfolio):
    print("\n==============================")
    print(_headline("SIMULIERTES DEPOT"))
    print("------------------------------")

    total = 0.0

    if not portfolio:
        print("Keine Positionen im simulierten Depot.")

    for symbol, pos in portfolio.items():
        value = pos["qty"] * pos["price_eur"]
        total += value
        value_str = colorize(value, f"{value:.2f} EUR")
        company = pos.get("company_name", symbol)

        if pos["native_currency"] == BASE_CURRENCY:
            print(f"{symbol} ({company}): {pos['qty']} Stück | Wert {value_str}")
        else:
            native_value = pos["qty"] * pos["price_native"]
            print(
                f"{symbol} ({company}): {pos['qty']} Stück | "
                f"Wert {value_str} | "
                f"{native_value:.2f} {pos['native_currency']}"
            )

    print("------------------------------")
    print(f"Depotwert: {colorize(total, f'{total:.2f} EUR')}")
    print("==============================\n")


def print_future_candidates(candidates):
    print("\n====================================================")
    print(_headline("TOP-KANDIDATEN FÜR DIE BEOBACHTUNG"))
    print("====================================================")

    if not candidates:
        print("Keine Kandidaten gefunden.")
        print("====================================================\n")
        return

    for i, c in enumerate(candidates, 1):
        reasons = ", ".join(c.get("reasons", [])) if c.get("reasons") else "keine klare Begründung"
        company = c.get("company_name", c["symbol"])

        print(
            f"{i}. {c['symbol']} ({company}) | "
            f"{colorize_signal(c['future_signal'])} | "
            f"Score: {c['score']:.2f} | "
            f"Stärke: {c['strength']} | "
            f"Risiko: {c['risk']}"
        )
        print(f"   Grund: {reasons}")

        if PRO_MODE and c.get("future_signal") == "BUY" and c.get("risk") == "hoch":
            print(f"   {_warning_line('Kaufsignal bei hohem Risiko.')}")

    print("====================================================\n")


def print_future_candidates_compact(candidates):
    print("\n====================================================")
    print(_headline("TOP-KANDIDATEN FÜR DIE BEOBACHTUNG"))
    print("====================================================")

    if not candidates:
        print("Keine Kandidaten gefunden.")
        print("====================================================\n")
        return

    for i, c in enumerate(candidates, 1):
        company = c.get("company_name", c["symbol"])
        print(
            f"{i}. {c['symbol']} ({company}) | "
            f"{colorize_signal(c['future_signal'])} | "
            f"Score: {c['score']:.2f} | "
            f"Stärke: {c['strength']} | "
            f"Risiko: {c['risk']}"
        )

    print("====================================================\n")


def print_financial_overview(start, end, pnl, currency, pnl_native):
    print("\n==============================")
    print(_headline("FINANZÜBERSICHT DER SIMULATION"))
    print("------------------------------")
    print(f"Start     : {start:.2f} EUR")
    print(f"Stand     : {end:.2f} EUR")
    print(f"Differenz : {colorize(pnl, f'{pnl:.2f} EUR')}")
    if currency != BASE_CURRENCY:
        print(f"Info      : {pnl_native:.2f} {currency}")
    if PRO_MODE and pnl < 0:
        print(_warning_line("Simulation aktuell im Minus."))
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
    print(_headline(f"DEPOTWERT-KURVE {symbol}"))
    print("------------------------------")
    print(line)
    print(f"Start: {values[0]:.2f}")
    print(f"Ende: {values[-1]:.2f}")
    if PRO_MODE:
        delta = values[-1] - values[0]
        print(f"Delta: {colorize(delta, f'{delta:.2f} EUR')}")
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
        reason = t.get("reason")
        if reason:
            print(f"{t['buy_time']} -> {t['sell_time']} | {pnl_str} | Grund: {reason}")
        else:
            print(f"{t['buy_time']} -> {t['sell_time']} | {pnl_str}")


def print_diagnostics(info):
    print("\n------------------------------")
    print(_headline(f"DIAGNOSE {info['symbol']}"))
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

    if PRO_MODE:
        blockers = []
        if not info.get("trend_ok"):
            blockers.append("Trend")
        if not info.get("breakout_ok"):
            blockers.append("Breakout")
        if not info.get("momentum_ok"):
            blockers.append("Momentum")
        if blockers:
            print(_warning_line(f"Blocker: {', '.join(blockers)}"))

    print("------------------------------\n")


def print_buy_overview(candidates):
    print("\n====================================================")
    print(_headline("BEOBACHTUNGSSIGNALE"))
    print("====================================================")

    filtered = [c for c in candidates if c["future_signal"] in ("BUY", "WATCH")]

    if not filtered:
        print("Keine BUY/WATCH Kandidaten gefunden.")
        print("====================================================\n")
        return

    for i, c in enumerate(filtered, 1):
        company = c.get("company_name", c["symbol"])
        prefix = "► " if PRO_MODE and c["future_signal"] == "BUY" else ""
        print(
            f"{prefix}{i}. {c['symbol']} ({company}) | "
            f"{colorize_signal(c['future_signal'])} | "
            f"Score: {c['score']:.2f} | "
            f"Stärke: {c['strength']} | "
            f"Risiko: {c['risk']}"
        )

    print("====================================================\n")


def print_buy_blockers_summary(blockers):
    print("\n====================================================")
    print(_headline("WARUM GIBT ES KAUM BUY-SIGNALE?"))
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
    print(_headline("LAUFZEIT"))
    print("------------------------------")
    print(f"{seconds:.2f} Sekunden")
    if PRO_MODE and seconds > 120:
        print(_warning_line("Laufzeit ist relativ hoch."))
    print("==============================\n")


def print_explanations():
    if not BEGINNER_MODE:
        return

    print("\n==============================")
    print("EINSTEIGER-HILFE")
    print("------------------------------")
    print("P/L")
    print("  Bedeutet Profit/Loss, also Gewinn oder Verlust.")
    print("  Positiv = Gewinn, negativ = Verlust.\n")

    print("Trades")
    print("  Anzahl abgeschlossener Simulations-Trades.")
    print("  Ein Trade ist typischerweise ein kompletter Kauf-Verkauf-Zyklus.\n")

    print("Trefferquote")
    print("  Anteil der Gewinntrades in Prozent.")
    print("  Beispiel: 60 % heißt, 6 von 10 Trades waren profitabel.\n")

    print("Score")
    print("  Interne Bewertungszahl des Systems.")
    print("  Höher bedeutet: Aktie sieht nach den Regeln des Modells interessanter aus.\n")

    print("BUY / WATCH / SELL / HOLD")
    print("  BUY   = im Modell attraktiv")
    print("  WATCH = beobachten")
    print("  SELL  = im Modell eher schwach / Ausstiegssignal")
    print("  HOLD  = halten / keine klare Änderung\n")

    print("Wichtig")
    print("  Das alles ist nur Simulation und keine Anlageberatung.")
    print("==============================\n")
