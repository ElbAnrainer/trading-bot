from config import BASE_CURRENCY
import shutil

from security_identifiers import identifiers_text
from text_tables import format_table_row, format_table_separator, pad_visible, visible_len


try:
    LINE_WIDTH = min(120, shutil.get_terminal_size().columns)
except Exception:
    LINE_WIDTH = 80


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
        return str(text)
    return "".join(styles) + str(text) + RESET


def _line(char="="):
    return char * LINE_WIDTH


def _subline(char="-"):
    return char * LINE_WIDTH


def _format_row(text):
    text = str(text)
    if visible_len(text) > LINE_WIDTH:
        return pad_visible(text, LINE_WIDTH)
    return pad_visible(text, LINE_WIDTH)


def _print_block(title, lines, line_char="="):
    print("\n" + (line_char * LINE_WIDTH))
    print(_format_row(title))
    print(line_char * LINE_WIDTH)
    for line in lines:
        print(_format_row(line))
    print(line_char * LINE_WIDTH + "\n")


def _headline(text):
    return _style(text, BOLD) if PRO_MODE else text


def _warning_line(text):
    if PRO_MODE:
        return _style(f"⚠ {text}", YELLOW, BOLD)
    return text


def _identifier_line(isin, wkn, prefix="    "):
    return f"{prefix}{identifiers_text(isin, wkn)}"


def colorize(value, text):
    if value > 0:
        return _style(text, GREEN)
    if value < 0:
        return _style(text, RED)
    return str(text)


def colorize_signal(signal):
    if signal == "BUY":
        return _style(signal, GREEN, BOLD) if PRO_MODE else signal
    if signal == "SELL":
        return _style(signal, RED, BOLD) if PRO_MODE else signal
    if signal == "WATCH":
        return _style(signal, YELLOW, BOLD) if PRO_MODE else signal
    if signal == "HOLD":
        return _style(signal, CYAN) if PRO_MODE else signal
    return str(signal)


def print_simulation_notice():
    lines = [
        "Dieses System arbeitet nur mit Simulationsdaten.",
        "Es werden keine echten Orders ausgeführt.",
        "Es besteht keine Broker-Anbindung.",
        "Keine Anlageberatung.",
    ]
    _print_block(_headline("SIMULATIONSHINWEIS"), lines)


def print_summary_only(closed_trades, native_currency):
    total = len(closed_trades)
    wins = sum(1 for t in closed_trades if float(t.get("pnl_eur", 0.0)) > 0)
    losses = sum(1 for t in closed_trades if float(t.get("pnl_eur", 0.0)) < 0)
    total_pnl = sum(float(t.get("pnl_eur", 0.0)) for t in closed_trades)
    avg_trade = (total_pnl / total) if total else 0.0
    hit = (wins / total * 100.0) if total else 0.0

    lines = [
        f"Abgeschlossene Trades : {total}",
        f"Gewinntrades          : {wins}",
        f"Verlusttrades         : {losses}",
        f"Trefferquote          : {hit:.2f} %",
        f"Ø Trade P/L           : {colorize(avg_trade, f'{avg_trade:.2f} EUR')}",
        f"Gesamt P/L            : {colorize(total_pnl, f'{total_pnl:.2f} EUR')}",
    ]

    if PRO_MODE and hit < 45 and total >= 5:
        lines.append(_warning_line("Trefferquote ist schwach."))

    _print_block(_headline("SIMULATIONSERGEBNIS (EUR)"), lines)


def print_ranking(results):
    if not results:
        _print_block(_headline("PERFORMANCE-RANKING"), ["Keine Backtest-Ergebnisse vorhanden."])
        return

    columns = [
        ("Nr", 3, ">"),
        ("Sym", 6, "<"),
        ("Unternehmen", 22, "<"),
        ("P/L EUR", 12, ">"),
        ("P/L %", 7, ">"),
        ("Treffer", 8, ">"),
        ("Trades", 6, ">"),
        ("Signal", 6, "<"),
    ]
    lines = []
    lines.append(format_table_row(columns))
    lines.append(format_table_separator(columns))
    for i, r in enumerate(results, 1):
        pnl = float(r.get("pnl_eur", 0.0))
        pnl_pct = float(r.get("pnl_pct_eur", 0.0))
        hit_rate = float(r.get("hit_rate_pct", 0.0))
        trades = int(r.get("trade_count", 0))
        symbol = r.get("symbol", "-")
        company = r.get("company_name", symbol)
        signal = r.get("signal", "")
        rank_label = f"★{i}" if PRO_MODE and i == 1 else f"{i}."
        lines.append(
            format_table_row(
                [
                    (rank_label, 3, ">"),
                    (symbol, 6, "<"),
                    (company, 22, "<"),
                    (colorize(pnl, f"{pnl:.2f}"), 12, ">"),
                    (f"{pnl_pct:.2f}%", 7, ">"),
                    (f"{hit_rate:.2f}%", 8, ">"),
                    (str(trades), 6, ">"),
                    (colorize_signal(signal or "-"), 6, "<"),
                ]
            )
        )
        lines.append(_identifier_line(r.get("isin"), r.get("wkn")))

    _print_block(_headline("PERFORMANCE-RANKING DER BESTEN BACKTESTS"), lines)


def print_recommendation(symbol, signal, price_eur, price_native, native_currency, isin="-", wkn="-"):
    signal_str = colorize_signal(signal)

    if native_currency == BASE_CURRENCY:
        line = f"{symbol}: {signal_str} @ {price_eur:.2f} EUR"
    else:
        line = (
            f"{symbol}: {signal_str} @ {price_eur:.2f} EUR "
            f"(Handel: {price_native:.2f} {native_currency})"
        )

    if PRO_MODE and signal == "SELL":
        line = _warning_line(line)

    print(_format_row(line))
    print(_format_row(_identifier_line(isin, wkn, prefix="      ")))


def print_portfolio(portfolio):
    if not portfolio:
        _print_block(_headline("SIMULIERTES DEPOT"), ["Keine Positionen im simulierten Depot."])
        return

    columns = [
        ("Sym", 6, "<"),
        ("Unternehmen", 22, "<"),
        ("Qty", 5, ">"),
        ("Wert EUR", 12, ">"),
        ("Wert nativ", 14, ">"),
    ]
    total = 0.0
    lines = [format_table_row(columns), format_table_separator(columns)]

    for symbol, pos in portfolio.items():
        qty = float(pos["qty"])
        price_eur = float(pos["price_eur"])
        value = qty * price_eur
        total += value
        company = pos.get("company_name", symbol)
        native_value_text = "-"

        if pos["native_currency"] != BASE_CURRENCY:
            native_value = qty * float(pos["price_native"])
            native_value_text = f"{native_value:.2f} {pos['native_currency']}"

        lines.append(
            format_table_row(
                [
                    (symbol, 6, "<"),
                    (company, 22, "<"),
                    (str(int(qty)), 5, ">"),
                    (colorize(value, f"{value:.2f}"), 12, ">"),
                    (native_value_text, 14, ">"),
                ]
            )
        )
        lines.append(_identifier_line(pos.get("isin"), pos.get("wkn")))

    lines.append(_subline("-"))
    lines.append(f"Depotwert: {colorize(total, f'{total:.2f} EUR')}")

    _print_block(_headline("SIMULIERTES DEPOT"), lines)


def print_future_candidates(candidates):
    if not candidates:
        _print_block(_headline("TOP-KANDIDATEN FÜR DIE BEOBACHTUNG"), ["Keine Kandidaten gefunden."])
        return

    columns = [
        ("Nr", 3, ">"),
        ("Sym", 6, "<"),
        ("Unternehmen", 20, "<"),
        ("Signal", 6, "<"),
        ("Score", 7, ">"),
        ("Stärke", 6, "<"),
        ("Risiko", 6, "<"),
    ]
    lines = []
    lines.append(format_table_row(columns))
    lines.append(format_table_separator(columns))
    for i, c in enumerate(candidates, 1):
        company = c.get("company_name", c["symbol"])
        reasons = ", ".join(c.get("reasons", [])) if c.get("reasons") else "keine klare Begründung"

        lines.append(
            format_table_row(
                [
                    (f"{i}.", 3, ">"),
                    (c["symbol"], 6, "<"),
                    (company, 20, "<"),
                    (colorize_signal(c["future_signal"]), 6, "<"),
                    (f"{c['score']:.2f}", 7, ">"),
                    (c["strength"], 6, "<"),
                    (c["risk"], 6, "<"),
                ]
            )
        )
        lines.append(_identifier_line(c.get("isin"), c.get("wkn")))
        lines.append(f"    Grund: {reasons}")

        if PRO_MODE and c.get("future_signal") == "BUY" and c.get("risk") == "hoch":
            lines.append(f"    {_warning_line('Kaufsignal bei hohem Risiko.')}")

    _print_block(_headline("TOP-KANDIDATEN FÜR DIE BEOBACHTUNG"), lines)


def print_future_candidates_compact(candidates):
    if not candidates:
        _print_block(_headline("TOP-KANDIDATEN FÜR DIE BEOBACHTUNG"), ["Keine Kandidaten gefunden."])
        return

    columns = [
        ("Nr", 3, ">"),
        ("Sym", 6, "<"),
        ("Unternehmen", 20, "<"),
        ("Signal", 6, "<"),
        ("Score", 7, ">"),
        ("Stärke", 6, "<"),
        ("Risiko", 6, "<"),
    ]
    lines = []
    lines.append(format_table_row(columns))
    lines.append(format_table_separator(columns))
    for i, c in enumerate(candidates, 1):
        company = c.get("company_name", c["symbol"])
        lines.append(
            format_table_row(
                [
                    (f"{i}.", 3, ">"),
                    (c["symbol"], 6, "<"),
                    (company, 20, "<"),
                    (c["future_signal"], 6, "<"),
                    (f"{c['score']:.2f}", 7, ">"),
                    (c["strength"], 6, "<"),
                    (c["risk"], 6, "<"),
                ]
            )
        )
        lines.append(_identifier_line(c.get("isin"), c.get("wkn")))

    _print_block(_headline("TOP-KANDIDATEN FÜR DIE BEOBACHTUNG"), lines)


def print_financial_overview(start, end, pnl, currency, pnl_native):
    lines = [
        f"Start     : {start:.2f} EUR",
        f"Stand     : {end:.2f} EUR",
        f"Differenz : {colorize(pnl, f'{pnl:.2f} EUR')}",
    ]

    if currency != BASE_CURRENCY:
        lines.append(f"Info      : {pnl_native:.2f} {currency}")

    if PRO_MODE and pnl < 0:
        lines.append(_warning_line("Simulation aktuell im Minus."))

    _print_block(_headline("FINANZÜBERSICHT DER SIMULATION"), lines)


def print_equity_curve_terminal(symbol, curve, isin="-", wkn="-"):
    if not curve:
        return

    values = [float(p["equity_eur"]) for p in curve]
    blocks = "▁▂▃▄▅▆▇█"

    min_v = min(values)
    max_v = max(values)

    if max_v == min_v:
        spark = "─" * min(len(values), max(10, LINE_WIDTH - 10))
    else:
        usable = values[: max(10, LINE_WIDTH - 10)]
        chars = []
        for v in usable:
            idx = int((v - min_v) / (max_v - min_v) * (len(blocks) - 1))
            chars.append(blocks[idx])
        spark = "".join(chars)

    lines = [
        identifiers_text(isin, wkn),
        spark,
        f"Start: {values[0]:.2f}",
        f"Ende: {values[-1]:.2f}",
    ]

    if PRO_MODE:
        delta = values[-1] - values[0]
        lines.append(f"Delta: {colorize(delta, f'{delta:.2f} EUR')}")

    _print_block(_headline(f"DEPOTWERT-KURVE {symbol}"), lines)


def print_closed_trades(symbol, name, isin, wkn, trades, currency):
    if not trades:
        return

    lines = [
        f"{name}",
        f"ISIN: {isin} | WKN: {wkn} | Währung: {currency}",
    ]
    columns = [
        ("Kauf", 16, "<"),
        ("Verkauf", 16, "<"),
        ("P/L EUR", 12, ">"),
        ("Grund", 24, "<"),
    ]
    lines.append(format_table_row(columns))
    lines.append(format_table_separator(columns))

    for t in trades:
        pnl_eur = float(t.get("pnl_eur", 0.0))
        pnl_str = colorize(pnl_eur, f"{pnl_eur:.2f} EUR")
        buy_time = t.get("buy_time", "-")
        sell_time = t.get("sell_time", "-")
        reason = t.get("reason", "-")

        lines.append(
            format_table_row(
                [
                    (buy_time, 16, "<"),
                    (sell_time, 16, "<"),
                    (pnl_str, 12, ">"),
                    (reason, 24, "<"),
                ]
            )
        )

    _print_block(_headline(f"DETAILS {symbol}"), lines)


def print_diagnostics(info):
    def yn(v):
        return "JA" if v else "NEIN"

    lines = [
        identifiers_text(info.get("isin"), info.get("wkn")),
        f"Trend                : {yn(info.get('trend_ok'))}",
        f"Breakout             : {yn(info.get('breakout_ok'))}",
        f"Momentum             : {yn(info.get('momentum_ok'))}",
        f"Volatilität          : {yn(info.get('volatility_ok'))}",
        f"Relative Stärke      : {yn(info.get('relative_strength_ok'))}",
    ]

    rs = info.get("relative_strength_pct")
    if rs is not None:
        lines.append(f"RS vs Markt          : {rs:.2f}%")

    lines.extend(
        [
            f"Fundamental Score    : {info.get('fundamental_score')}",
            f"Score                : {info.get('score'):.2f}",
            f"Aktuell              : {info.get('current_signal')}",
            f"Zukunft              : {info.get('future_signal')}",
        ]
    )

    if PRO_MODE:
        blockers = []
        if not info.get("trend_ok"):
            blockers.append("Trend")
        if not info.get("breakout_ok"):
            blockers.append("Breakout")
        if not info.get("momentum_ok"):
            blockers.append("Momentum")
        if blockers:
            lines.append(_warning_line(f"Blocker: {', '.join(blockers)}"))

    _print_block(_headline(f"DIAGNOSE {info['symbol']}"), lines, line_char="-")


def print_buy_overview(candidates):
    filtered = [c for c in candidates if c["future_signal"] in ("BUY", "WATCH")]

    if not filtered:
        _print_block(_headline("BEOBACHTUNGSSIGNALE"), ["Keine BUY/WATCH Kandidaten gefunden."])
        return

    columns = [
        ("Nr", 3, ">"),
        ("Sym", 6, "<"),
        ("Unternehmen", 20, "<"),
        ("Signal", 6, "<"),
        ("Score", 7, ">"),
        ("Stärke", 6, "<"),
        ("Risiko", 6, "<"),
    ]
    lines = []
    lines.append(format_table_row(columns))
    lines.append(format_table_separator(columns))
    for i, c in enumerate(filtered, 1):
        company = c.get("company_name", c["symbol"])
        rank_label = f"►{i}" if PRO_MODE and c["future_signal"] == "BUY" else f"{i}."
        lines.append(
            format_table_row(
                [
                    (rank_label, 3, ">"),
                    (c["symbol"], 6, "<"),
                    (company, 20, "<"),
                    (colorize_signal(c["future_signal"]), 6, "<"),
                    (f"{c['score']:.2f}", 7, ">"),
                    (c["strength"], 6, "<"),
                    (c["risk"], 6, "<"),
                ]
            )
        )
        lines.append(_identifier_line(c.get("isin"), c.get("wkn")))

    _print_block(_headline("BEOBACHTUNGSSIGNALE"), lines)


def print_buy_blockers_summary(blockers):
    if not blockers:
        _print_block(_headline("WARUM GIBT ES KAUM BUY-SIGNALE?"), ["Keine Blocker erkannt."])
        return

    lines = []
    sorted_items = sorted(blockers.items(), key=lambda x: x[1], reverse=True)

    for i, (name, count) in enumerate(sorted_items, 1):
        if count <= 0:
            continue
        lines.append(f"{i}. {name:<24}: {count} Aktien")

    if not lines:
        lines.append("Keine relevanten Blocker erkannt.")

    _print_block(_headline("WARUM GIBT ES KAUM BUY-SIGNALE?"), lines)


def print_runtime(seconds):
    lines = [f"{seconds:.2f} Sekunden"]

    if PRO_MODE and seconds > 120:
        lines.append(_warning_line("Laufzeit ist relativ hoch."))

    _print_block(_headline("LAUFZEIT"), lines)


def print_explanations():
    if not BEGINNER_MODE:
        return

    lines = [
        "P/L = Gewinn oder Verlust",
        "Trades = Anzahl abgeschlossener Simulations-Trades",
        "Trefferquote = Anteil der Gewinntrades in Prozent",
        "Score = interne Bewertungszahl des Systems",
        "BUY = attraktiv | WATCH = beobachten | SELL = eher schwach | HOLD = neutral",
        "Wichtig: Das alles ist nur Simulation und keine Anlageberatung.",
    ]

    _print_block("EINSTEIGER-HILFE", lines)
