from config import BASE_CURRENCY

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

LINE_WIDTH = 96
LABEL_WIDTH = 26
SYMBOL_WIDTH = 8
NAME_WIDTH = 28
SIGNAL_WIDTH = 14
STRENGTH_WIDTH = 7
RISK_WIDTH = 7
SCORE_WIDTH = 8


def line(char="="):
    return char * LINE_WIDTH


def separator():
    return "-" * LINE_WIDTH


def header(title):
    print("\n" + line("="))
    print(title.center(LINE_WIDTH))
    print(line("="))


def footer():
    print(line("=") + "\n")


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


def _fit_text(text, width):
    text = str(text or "")
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def print_simulation_notice():
    header("SIMULATIONSHINWEIS")
    print("Dieses System dient nur der Simulation, dem Backtesting und der Analyse.")
    print("Es werden keine echten Orders ausgeführt und keine Broker angesprochen.")
    print("Die Ausgabe ist keine Anlageberatung. Echte Entscheidungen müssen")
    print("immer manuell durch den Nutzer getroffen werden.")
    footer()


def print_summary_only(closed_trades, native_currency):
    total_pnl_eur = sum(t.get("pnl_eur", 0.0) for t in closed_trades)

    wins = sum(1 for t in closed_trades if t.get("pnl_eur", 0.0) > 0)
    losses = sum(1 for t in closed_trades if t.get("pnl_eur", 0.0) < 0)
    total = len(closed_trades)

    hit = (wins / total * 100) if total else 0.0
    pnl_str = colorize(total_pnl_eur, f"{total_pnl_eur:.2f} EUR")

    header("SIMULATIONSERGEBNIS (EUR)")
    print(f"{'Abgeschlossene Trades':<{LABEL_WIDTH}}: {total}")
    print(f"{'Gewinntrades':<{LABEL_WIDTH}}: {wins}")
    print(f"{'Verlusttrades':<{LABEL_WIDTH}}: {losses}")
    print(f"{'Trefferquote':<{LABEL_WIDTH}}: {hit:.2f} %")
    print(f"{'Gesamt P/L':<{LABEL_WIDTH}}: {pnl_str}")
    footer()


def print_ranking(results):
    header("RANKING DER BESTEN BACKTESTS (EUR)")

    if not results:
        print("Keine Ergebnisse vorhanden.")
        footer()
        return

    for i, r in enumerate(results, 1):
        pnl = r["pnl_eur"]
        pnl_str = colorize(pnl, f"{pnl:.2f} EUR")
        company_name = _fit_text(r.get("company_name", ""), NAME_WIDTH)

        print(
            f"{i:>2}. "
            f"{r['symbol']:<{SYMBOL_WIDTH}} "
            f"{company_name:<{NAME_WIDTH}} | "
            f"{pnl_str:>18} | "
            f"{r['pnl_pct_eur']:>7.2f}% | "
            f"Trades: {r['trade_count']:>3}"
        )

    footer()


def print_recommendation(symbol, signal, price_eur, price_native, native_currency):
    signal_str = colorize_signal(signal)

    if native_currency == BASE_CURRENCY:
        print(
            f"{symbol:<{SYMBOL_WIDTH}}: "
            f"{signal_str:<{SIGNAL_WIDTH}} @ {price_eur:>9.2f} EUR"
        )
    else:
        print(
            f"{symbol:<{SYMBOL_WIDTH}}: "
            f"{signal_str:<{SIGNAL_WIDTH}} @ {price_eur:>9.2f} EUR "
            f"(Handelswährung: {price_native:.2f} {native_currency})"
        )


def print_portfolio(portfolio):
    header("SIMULIERTES DEPOT (EUR)")

    total = 0.0

    if not portfolio:
        print("Keine Positionen im simulierten Depot.")
        footer()
        return

    for symbol, pos in portfolio.items():
        value = pos["qty"] * pos["price_eur"]
        total += value
        value_str = colorize(value, f"{value:.2f} EUR")
        company_name = _fit_text(pos.get("company_name", ""), NAME_WIDTH)

        if pos["native_currency"] == BASE_CURRENCY:
            print(
                f"{symbol:<{SYMBOL_WIDTH}} "
                f"{company_name:<{NAME_WIDTH}} | "
                f"Stück: {pos['qty']:>4} | "
                f"Wert: {value_str:>16}"
            )
        else:
            native_value = pos["qty"] * pos["price_native"]
            print(
                f"{symbol:<{SYMBOL_WIDTH}} "
                f"{company_name:<{NAME_WIDTH}} | "
                f"Stück: {pos['qty']:>4} | "
                f"Wert: {value_str:>16} | "
                f"{native_value:>10.2f} {pos['native_currency']}"
            )

    print(separator())
    print(f"{'Depotwert':<{LABEL_WIDTH}}: {colorize(total, f'{total:.2f} EUR')}")
    footer()


def print_future_candidates(candidates):
    header("TOP-KANDIDATEN FÜR DIE BEOBACHTUNG")

    if not candidates:
        print("Keine Kandidaten gefunden.")
        footer()
        return

    for i, c in enumerate(candidates, 1):
        reasons = ", ".join(c.get("reasons", [])) if c.get("reasons") else "keine klare Begründung"
        company_name = _fit_text(c.get("company_name", ""), NAME_WIDTH)

        print(
            f"{i:>2}. "
            f"{c['symbol']:<{SYMBOL_WIDTH}} "
            f"{company_name:<{NAME_WIDTH}} | "
            f"{colorize_signal(c['future_signal']):<{SIGNAL_WIDTH}} | "
            f"Score: {c['score']:>{SCORE_WIDTH}.2f} | "
            f"Stärke: {c['strength']:<{STRENGTH_WIDTH}} | "
            f"Risiko: {c['risk']:<{RISK_WIDTH}}"
        )
        print(f"    Grund: {reasons}")

    footer()


def print_future_candidates_compact(candidates):
    header("TOP-KANDIDATEN (KURZ)")

    if not candidates:
        print("Keine Kandidaten gefunden.")
        footer()
        return

    for i, c in enumerate(candidates, 1):
        company_name = _fit_text(c.get("company_name", ""), NAME_WIDTH)

        print(
            f"{i:>2}. "
            f"{c['symbol']:<{SYMBOL_WIDTH}} "
            f"{company_name:<{NAME_WIDTH}} | "
            f"{colorize_signal(c['future_signal']):<{SIGNAL_WIDTH}} | "
            f"Score: {c['score']:>{SCORE_WIDTH}.2f} | "
            f"Stärke: {c['strength']:<{STRENGTH_WIDTH}} | "
            f"Risiko: {c['risk']:<{RISK_WIDTH}}"
        )

    footer()


def print_financial_overview(start, end, pnl, currency, pnl_native):
    header("FINANZÜBERSICHT DER SIMULATION")
    print(f"{'Start':<{LABEL_WIDTH}}: {start:.2f} EUR")
    print(f"{'Stand':<{LABEL_WIDTH}}: {end:.2f} EUR")
    print(f"{'Differenz':<{LABEL_WIDTH}}: {colorize(pnl, f'{pnl:.2f} EUR')}")
    if currency != BASE_CURRENCY:
        print(f"{'Info':<{LABEL_WIDTH}}: {pnl_native:.2f} {currency}")
    footer()


def print_equity_curve_terminal(symbol, curve):
    if not curve:
        return

    values = [p["equity_eur"] for p in curve]

    blocks = "▁▂▃▄▅▆▇█"
    min_v = min(values)
    max_v = max(values)

    if max_v == min_v:
        line_str = "─" * len(values)
    else:
        line_str = ""
        for v in values:
            idx = int((v - min_v) / (max_v - min_v) * (len(blocks) - 1))
            line_str += blocks[idx]

    header(f"DEPOTWERT-KURVE {symbol}")
    print(line_str)
    print(f"Start: {values[0]:.2f}")
    print(f"Ende: {values[-1]:.2f}")
    footer()


def print_closed_trades(symbol, name, isin, wkn, trades, currency):
    if not trades:
        return

    header(f"DETAILS {symbol}")
    print(name)
    print(f"ISIN: {isin} | WKN: {wkn} | Währung: {currency}")
    print(separator())

    for t in trades:
        pnl_eur = t.get("pnl_eur", 0.0)
        pnl_str = colorize(pnl_eur, f"{pnl_eur:.2f} EUR")
        print(f"{t['buy_time']} -> {t['sell_time']} | {pnl_str:>14}")

    footer()


def print_diagnostics(info):
    header(f"DIAGNOSE {info['symbol']}")

    def yn(v):
        return "JA" if v else "NEIN"

    print(f"{'Trend':<{LABEL_WIDTH}}: {yn(info.get('trend_ok'))}")
    print(f"{'Breakout':<{LABEL_WIDTH}}: {yn(info.get('breakout_ok'))}")
    print(f"{'Momentum':<{LABEL_WIDTH}}: {yn(info.get('momentum_ok'))}")
    print(f"{'Volatilität':<{LABEL_WIDTH}}: {yn(info.get('volatility_ok'))}")
    print(f"{'Relative Stärke':<{LABEL_WIDTH}}: {yn(info.get('relative_strength_ok'))}")

    rs = info.get("relative_strength_pct")
    if rs is not None:
        print(f"{'RS vs Markt':<{LABEL_WIDTH}}: {rs:.2f}%")

    print(f"{'Fundamental Score':<{LABEL_WIDTH}}: {info.get('fundamental_score')}")
    print(f"{'Score':<{LABEL_WIDTH}}: {info.get('score'):.2f}")

    components = info.get("score_components", {})
    if components:
        print(separator())
        print("Score-Aufschlüsselung:")
        print(f"{'Trendbonus':<{LABEL_WIDTH}}: {components.get('trend_bonus', 0):.2f}")
        print(f"{'Breakoutbonus':<{LABEL_WIDTH}}: {components.get('breakout_bonus', 0):.2f}")
        print(f"{'Momentumbonus':<{LABEL_WIDTH}}: {components.get('momentum_bonus', 0):.2f}")
        print(f"{'Momentum-Anteil':<{LABEL_WIDTH}}: {components.get('momentum_component', 0):.2f}")
        print(f"{'Volatilitätsanteil':<{LABEL_WIDTH}}: {components.get('volatility_component', 0):.2f}")
        print(f"{'Relative Stärke':<{LABEL_WIDTH}}: {components.get('relative_strength_bonus', 0):.2f}")
        print(f"{'Fundamentaldaten':<{LABEL_WIDTH}}: {components.get('fundamental_bonus', 0):.2f}")

    print(separator())
    print(f"{'Aktuell':<{LABEL_WIDTH}}: {info.get('current_signal')}")
    print(f"{'Zukunft':<{LABEL_WIDTH}}: {info.get('future_signal')}")
    footer()


def print_buy_overview(candidates):
    header("BEOBACHTUNGSSIGNALE (ÜBERSICHT)")

    filtered = [c for c in candidates if c["future_signal"] in ("BUY", "WATCH")]

    if not filtered:
        print("Keine BUY/WATCH-Kandidaten gefunden.")
        footer()
        return

    for i, c in enumerate(filtered, 1):
        company_name = _fit_text(c.get("company_name", ""), NAME_WIDTH)
        print(
            f"{i:>2}. "
            f"{c['symbol']:<{SYMBOL_WIDTH}} "
            f"{company_name:<{NAME_WIDTH}} | "
            f"{colorize_signal(c['future_signal']):<{SIGNAL_WIDTH}} | "
            f"Score: {c['score']:>{SCORE_WIDTH}.2f} | "
            f"Stärke: {c['strength']:<{STRENGTH_WIDTH}} | "
            f"Risiko: {c['risk']:<{RISK_WIDTH}}"
        )

    footer()


def print_buy_blockers_summary(blockers):
    header("WARUM GIBT ES KAUM BUY-SIGNALE?")

    if not blockers:
        print("Keine Blocker erkannt.")
        footer()
        return

    sorted_items = sorted(blockers.items(), key=lambda x: x[1], reverse=True)

    index = 1
    for name, count in sorted_items:
        if count <= 0:
            continue
        print(f"{index:>2}. {name:<24}: {count:>4} Aktien")
        index += 1

    footer()


def print_runtime(seconds):
    header("LAUFZEIT")
    print(f"{seconds:.2f} Sekunden")
    print(separator())
    print("Hinweis: Dieses System erzeugt nur Simulations- und Beobachtungssignale.")
    print("Es werden keine automatischen Orders ausgeführt.")
    print("Echte Handelsentscheidungen müssen manuell durch den Nutzer getroffen werden.")
    footer()
