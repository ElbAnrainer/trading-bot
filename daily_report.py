import csv
import os
import xml.etree.ElementTree as ET
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from config import (
    DAILY_REPORT_CSV,
    DAILY_REPORT_HTML,
    DAILY_REPORT_PDF,
    DAILY_REPORT_TXT,
    DAILY_REPORT_XML,
    REPORTS_DIR as DEFAULT_REPORTS_DIR,
    ensure_reports_dir,
)
from dashboard import build_dashboard_data
from text_tables import format_table_row, format_table_separator


REPORTS_DIR = DEFAULT_REPORTS_DIR
TXT_PATH = DAILY_REPORT_TXT
HTML_PATH = DAILY_REPORT_HTML
CSV_PATH = DAILY_REPORT_CSV
XML_PATH = DAILY_REPORT_XML
PDF_PATH = DAILY_REPORT_PDF


def _ensure_reports_dir():
    ensure_reports_dir()


def _safe_get(stats, key, default=0):
    return stats.get(key, default)


def _safe_text(value, default="-"):
    text = str(value).strip() if value is not None else ""
    return text if text else default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _analysis_source_label(source):
    mapping = {
        "current_run": "Aktueller CLI-Lauf",
        "latest_run": "Letzter gespeicherter Lauf",
        "none": "Keine aktuelle Analyse",
    }
    return mapping.get(str(source), str(source))


def _explanation_lines(items, empty_message, prefix="  - "):
    lines = []
    for item in items:
        symbol = _safe_text(item.get("symbol"), "-")
        summary = _safe_text(item.get("explanation_summary"), "")
        if not summary:
            continue
        lines.append(f"{prefix}{symbol}: {summary}")
        for point in item.get("explanation_points", [])[:3]:
            text = _safe_text(point, "")
            if text:
                lines.append(f"      {text}")

    if lines:
        return lines
    return [empty_message]


def _explanation_html(items, empty_message):
    rows = []
    for item in items:
        symbol = _safe_text(item.get("symbol"), "-")
        summary = _safe_text(item.get("explanation_summary"), "")
        if not summary:
            continue
        meta = " | ".join(
            _safe_text(point, "")
            for point in item.get("explanation_points", [])[:3]
            if _safe_text(point, "")
        )
        meta_html = f"<div class='explanation-meta'>{meta}</div>" if meta else ""
        rows.append(f"<li><strong>{symbol}</strong>: {summary}{meta_html}</li>")

    if rows:
        return "<ul class='explanations'>" + "".join(rows) + "</ul>"
    return f"<p class='muted'>{empty_message}</p>"


def _explanation_pdf_lines(items):
    lines = []
    for item in items:
        symbol = _safe_text(item.get("symbol"), "-")
        summary = _safe_text(item.get("explanation_summary"), "")
        if not summary:
            continue
        lines.append(f"{symbol}: {summary}")
        for point in item.get("explanation_points", [])[:3]:
            text = _safe_text(point, "")
            if text:
                lines.append(f"  {text}")
    return lines


def _build_report_data():
    try:
        data = build_dashboard_data()
    except Exception as exc:
        return {
            "error": f"Performance konnte nicht geladen werden: {exc}",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "top_symbols": [],
        }

    perf = data.get("performance", {})
    analysis = data.get("analysis", {})
    state = data.get("state", {})
    profile = data.get("profile", {})
    risk = data.get("risk", {})

    top_symbols = perf.get("top_symbols") or [
        {
            "symbol": item.get("symbol", ""),
            "company": item.get("company", item.get("symbol", "")),
            "isin": item.get("isin", "-"),
            "wkn": item.get("wkn", "-"),
            "count": item.get("trades", 0),
        }
        for item in perf.get("ranking", [])[:5]
    ]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "analysis_source": analysis.get("source", "none"),
        "analysis_source_label": _analysis_source_label(analysis.get("source", "none")),
        "analysis_generated_at": _safe_text(analysis.get("generated_at"), "-"),
        "analysis_period": _safe_text(analysis.get("period"), "-"),
        "analysis_interval": _safe_text(analysis.get("interval"), "-"),
        "analysis_result_count": len(analysis.get("current_results", [])),
        "analysis_candidate_count": len(analysis.get("future_candidates", [])),
        "analysis_order_count": len(analysis.get("orders", [])),
        "current_results": analysis.get("current_results", [])[:5],
        "future_candidates": analysis.get("future_candidates", [])[:5],
        "trading_plan": analysis.get("trading_plan", [])[:5],
        "simulated_portfolio": analysis.get("simulated_portfolio", [])[:8],
        "orders": analysis.get("orders", [])[:8],
        "profile_name": _safe_text(profile.get("name"), "-"),
        "total_entries": _safe_get(perf, "total_entries", _safe_get(perf, "journal_entries", 0)),
        "buy_signals": _safe_get(perf, "buy_signals", 0),
        "sell_signals": _safe_get(perf, "sell_signals", 0),
        "watch_signals": _safe_get(perf, "watch_signals", 0),
        "hold_signals": _safe_get(perf, "hold_signals", 0),
        "stocks_total": _safe_get(perf, "stocks_total", _safe_get(perf, "unique_symbols", 0)),
        "closed_trades": _safe_get(perf, "closed_trades_count", _safe_get(perf, "closed_trades", 0)),
        "winning_trades": _safe_get(perf, "winning_trades_count", _safe_get(perf, "winning_trades", 0)),
        "losing_trades": _safe_get(perf, "losing_trades_count", _safe_get(perf, "losing_trades", 0)),
        "hit_rate": _safe_get(perf, "hit_rate_pct", _safe_get(perf, "hit_rate", 0.0)),
        "realized_pnl": _safe_get(perf, "realized_pnl_eur", _safe_get(perf, "realized_pnl", 0.0)),
        "avg_trade": _safe_get(perf, "avg_trade_pnl_eur", _safe_get(perf, "avg_trade_pnl", 0.0)),
        "top_symbols": top_symbols,
        "score_validation": perf.get("score_validation", []),
        "state_cash_eur": _safe_float(state.get("cash_eur")),
        "state_invested_eur": _safe_float(state.get("total_invested_eur")),
        "state_equity_eur": _safe_float(state.get("last_equity_eur")),
        "state_peak_equity_eur": _safe_float(state.get("peak_equity_eur")),
        "state_drawdown_pct": _safe_float(state.get("drawdown_pct")),
        "state_positions": _safe_get(state, "positions", 0),
        "state_updated_at": _safe_text(state.get("updated_at"), "-"),
        "risk_max_position_pct": _safe_float(risk.get("max_position_pct")) * 100.0,
        "risk_stop_loss_pct": _safe_float(risk.get("stop_loss_pct")) * 100.0,
        "risk_trailing_stop_pct": _safe_float(risk.get("trailing_stop_pct")) * 100.0,
        "risk_max_drawdown_pct": _safe_float(risk.get("max_drawdown_pct")) * 100.0,
    }


def _build_text_report(report):
    lines = [
        "========================================",
        " DAILY REPORT",
        "========================================",
        f"Erstellt am           : {report['generated_at']}",
        "",
    ]

    if "error" in report:
        lines.extend(
            [
                "STATUS                : FEHLER",
                f"Fehlermeldung         : {report['error']}",
                "",
                "Hinweis: Daily Report konnte nicht vollständig erstellt werden.",
            ]
        )
        return "\n".join(lines) + "\n"

    def _append_section(title):
        lines.extend(["", title, "----------------------------------------"])

    def _append_table(columns, rows, empty_message):
        if not rows:
            lines.append(empty_message)
            return
        lines.append(format_table_row(columns))
        lines.append(format_table_separator(columns))
        for row in rows:
            lines.append(format_table_row(row))

    def _append_explanations(title, items, empty_message):
        _append_section(title)
        lines.extend(_explanation_lines(items, empty_message))

    lines.extend(
        [
            "AKTUELLER ANALYSE-LAUF",
            "----------------------------------------",
            f"Quelle                : {report['analysis_source_label']}",
            f"Profil                : {report['profile_name']}",
            f"Analyse-Zeitpunkt     : {report['analysis_generated_at']}",
            f"Zeitraum              : {report['analysis_period']}",
            f"Intervall             : {report['analysis_interval']}",
            f"Analyse-Ergebnisse    : {report['analysis_result_count']}",
            f"Aktuelle Kandidaten   : {report['analysis_candidate_count']}",
            f"Aktuelle Orders       : {report['analysis_order_count']}",
        ]
    )

    _append_section("AKTUELLE ANALYSE-ERGEBNISSE")
    _append_table(
        [
            ("SYM", 6, "<"),
            ("ISIN", 12, "<"),
            ("WKN", 6, "<"),
            ("SIG", 5, "<"),
            ("TRD", 5, ">"),
            ("P/L EUR", 10, ">"),
            ("SCORE", 7, ">"),
        ],
        [
            [
                (item.get("symbol", "-"), 6, "<"),
                (item.get("isin", "-"), 12, "<"),
                (item.get("wkn", "-"), 6, "<"),
                (item.get("signal", "-"), 5, "<"),
                (str(item.get("trade_count", 0)), 5, ">"),
                (f"{_safe_float(item.get('pnl_eur')):.2f}", 10, ">"),
                (f"{_safe_float(item.get('score')):.2f}", 7, ">"),
            ]
            for item in report["current_results"]
        ],
        "Keine frischen Analyse-Ergebnisse verfügbar.",
    )
    _append_explanations(
        "WARUM DIESE ANALYSE-ERGEBNISSE",
        report["current_results"],
        "Keine aktuellen Analyse-Erklärungen verfügbar.",
    )

    _append_section("AKTUELLE KAUFKANDIDATEN")
    _append_table(
        [
            ("SYM", 6, "<"),
            ("ISIN", 12, "<"),
            ("WKN", 6, "<"),
            ("SIG", 5, "<"),
            ("SCORE", 7, ">"),
            ("LEARN", 7, ">"),
            ("NAME", 20, "<"),
        ],
        [
            [
                (item.get("symbol", "-"), 6, "<"),
                (item.get("isin", "-"), 12, "<"),
                (item.get("wkn", "-"), 6, "<"),
                (item.get("future_signal", "-"), 5, "<"),
                (f"{_safe_float(item.get('score')):.2f}", 7, ">"),
                (f"{_safe_float(item.get('learned_bonus')):+.2f}", 7, ">"),
                (item.get("company", item.get("company_name", "-")), 20, "<"),
            ]
            for item in report["future_candidates"]
        ],
        "Keine aktuellen Kaufkandidaten verfügbar.",
    )
    _append_explanations(
        "WARUM DIESE KANDIDATEN",
        report["future_candidates"],
        "Keine Kandidaten-Erklärungen verfügbar.",
    )

    _append_section("AKTUELLER TRADING-PLAN")
    _append_table(
        [
            ("SYM", 6, "<"),
            ("ISIN", 12, "<"),
            ("WKN", 6, "<"),
            ("GEW", 5, ">"),
            ("KAP EUR", 10, ">"),
            ("LEARN", 7, ">"),
            ("NAME", 20, "<"),
        ],
        [
            [
                (item.get("symbol", "-"), 6, "<"),
                (item.get("isin", "-"), 12, "<"),
                (item.get("wkn", "-"), 6, "<"),
                (f"{_safe_float(item.get('weight')):.2f}", 5, ">"),
                (f"{_safe_float(item.get('capital')):.2f}", 10, ">"),
                (f"{_safe_float(item.get('learned_score')):.2f}", 7, ">"),
                (item.get("company", item.get("company_name", "-")), 20, "<"),
            ]
            for item in report["trading_plan"]
        ],
        "Kein aktueller Trading-Plan verfügbar.",
    )
    _append_explanations(
        "WARUM DIESER TRADING-PLAN",
        report["trading_plan"],
        "Keine Plan-Erklärungen verfügbar.",
    )

    _append_section("AKTUELLE ORDERS")
    _append_table(
        [
            ("ACT", 5, "<"),
            ("SYM", 6, "<"),
            ("REASON", 24, "<"),
            ("KAP EUR", 10, ">"),
            ("GEW", 5, ">"),
            ("LEARN", 7, ">"),
        ],
        [
            [
                (item.get("action", "-"), 5, "<"),
                (item.get("symbol", "-"), 6, "<"),
                (_safe_text(item.get("reason_label"), item.get("reason", "-")), 24, "<"),
                (f"{_safe_float(item.get('capital')):.2f}", 10, ">"),
                (f"{_safe_float(item.get('weight')):.2f}", 5, ">"),
                (f"{_safe_float(item.get('learned_score')):.2f}", 7, ">"),
            ]
            for item in report["orders"]
        ],
        "Keine aktuellen Orders verfügbar.",
    )
    _append_explanations(
        "WARUM DIESE ORDERS",
        report["orders"],
        "Keine Order-Erklärungen verfügbar.",
    )

    _append_section("SIMULIERTES DEPOT (AKTUELLER LAUF)")
    _append_table(
        [
            ("SYM", 6, "<"),
            ("ISIN", 12, "<"),
            ("WKN", 6, "<"),
            ("QTY", 7, ">"),
            ("KURS", 10, ">"),
            ("WERT", 10, ">"),
            ("NAME", 20, "<"),
        ],
        [
            [
                (item.get("symbol", "-"), 6, "<"),
                (item.get("isin", "-"), 12, "<"),
                (item.get("wkn", "-"), 6, "<"),
                (f"{_safe_float(item.get('qty')):.2f}", 7, ">"),
                (f"{_safe_float(item.get('price_eur')):.2f}", 10, ">"),
                (f"{_safe_float(item.get('value_eur')):.2f}", 10, ">"),
                (item.get("company", item.get("company_name", "-")), 20, "<"),
            ]
            for item in report["simulated_portfolio"]
        ],
        "Kein simuliertes Depot aus dem aktuellen Lauf verfügbar.",
    )

    lines.extend(
        [
            "",
            "HISTORISCHE PERFORMANCE",
            "----------------------------------------",
            f"Journal-Einträge      : {report['total_entries']}",
            f"BUY Signale           : {report['buy_signals']}",
            f"SELL Signale          : {report['sell_signals']}",
            f"WATCH Signale         : {report['watch_signals']}",
            f"HOLD Signale          : {report['hold_signals']}",
            f"Aktien gesamt         : {report['stocks_total']}",
            "----------------------------------------",
            f"Geschlossene Trades   : {report['closed_trades']}",
            f"Gewinntrades          : {report['winning_trades']}",
            f"Verlusttrades         : {report['losing_trades']}",
            f"Trefferquote          : {report['hit_rate']:.2f} %",
            f"Realisierter P/L      : {report['realized_pnl']:.2f} EUR",
            f"Ø Trade P/L           : {report['avg_trade']:.2f} EUR",
        ]
    )

    _append_section("HISTORISCHE TOP-AKTIEN")
    _append_table(
        [
            ("SYM", 6, "<"),
            ("ISIN", 12, "<"),
            ("WKN", 6, "<"),
            ("ANZAHL", 6, ">"),
            ("NAME", 24, "<"),
        ],
        [
            [
                (item["symbol"], 6, "<"),
                (item.get("isin", "-"), 12, "<"),
                (item.get("wkn", "-"), 6, "<"),
                (str(item.get("count", 0)), 6, ">"),
                (item.get("company", item["symbol"]), 24, "<"),
            ]
            for item in report["top_symbols"]
        ],
        "Keine Top-Aktien verfügbar.",
    )

    lines.extend(
        [
            "",
            "MINI-SYSTEM / DEPOT-STATE",
            "----------------------------------------",
            f"Cash                  : {report['state_cash_eur']:.2f} EUR",
            f"Investiert            : {report['state_invested_eur']:.2f} EUR",
            f"Equity                : {report['state_equity_eur']:.2f} EUR",
            f"Peak Equity           : {report['state_peak_equity_eur']:.2f} EUR",
            f"Drawdown              : {report['state_drawdown_pct']:.2f} %",
            f"Offene Positionen     : {report['state_positions']}",
            f"State-Update          : {report['state_updated_at']}",
            "",
            "RISIKOPROFIL",
            "----------------------------------------",
            f"Max Position          : {report['risk_max_position_pct']:.0f} %",
            f"Stop-Loss             : {report['risk_stop_loss_pct']:.0f} %",
            f"Trailing Stop         : {report['risk_trailing_stop_pct']:.0f} %",
            f"Max Drawdown          : {report['risk_max_drawdown_pct']:.0f} %",
            "",
            "Hinweis: Nur Simulation. Keine Anlageberatung.",
        ]
    )

    return "\n".join(lines) + "\n"


def _build_html_report(report):
    if "error" in report:
        return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>Daily Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; background: #f5f7fb; color: #1f2937; }}
    .card {{ background: white; padding: 24px; border-radius: 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
    .error {{ color: #b91c1c; font-weight: bold; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Daily Report</h1>
    <p>Erstellt am: {report['generated_at']}</p>
    <p class="error">Fehler: {report['error']}</p>
  </div>
</body>
</html>
"""

    current_result_rows = ""
    for item in report["current_results"]:
        current_result_rows += (
            "<tr>"
            f"<td>{item.get('symbol', '-')}</td>"
            f"<td>{item.get('isin', '-')}</td>"
            f"<td>{item.get('wkn', '-')}</td>"
            f"<td>{item.get('signal', '-')}</td>"
            f"<td>{item.get('company', item.get('company_name', item.get('symbol', '-')))}</td>"
            f"<td>{_safe_float(item.get('pnl_eur')):.2f} EUR</td>"
            f"<td>{int(item.get('trade_count', 0))}</td>"
            f"<td>{_safe_float(item.get('score')):.2f}</td>"
            "</tr>"
        )

    if not current_result_rows:
        current_result_rows = "<tr><td colspan='8'>Keine frischen Analyse-Ergebnisse verfügbar.</td></tr>"

    candidate_rows = ""
    for item in report["future_candidates"]:
        candidate_rows += (
            "<tr>"
            f"<td>{item.get('symbol', '-')}</td>"
            f"<td>{item.get('isin', '-')}</td>"
            f"<td>{item.get('wkn', '-')}</td>"
            f"<td>{item.get('future_signal', '-')}</td>"
            f"<td>{item.get('company', item.get('company_name', item.get('symbol', '-')))}</td>"
            f"<td>{_safe_float(item.get('score')):.2f}</td>"
            f"<td>{_safe_float(item.get('learned_bonus')):+.2f}</td>"
            "</tr>"
        )

    if not candidate_rows:
        candidate_rows = "<tr><td colspan='7'>Keine aktuellen Kaufkandidaten verfügbar.</td></tr>"

    trading_plan_rows = ""
    for item in report["trading_plan"]:
        trading_plan_rows += (
            "<tr>"
            f"<td>{item.get('symbol', '-')}</td>"
            f"<td>{item.get('isin', '-')}</td>"
            f"<td>{item.get('wkn', '-')}</td>"
            f"<td>{item.get('company', item.get('company_name', item.get('symbol', '-')))}</td>"
            f"<td>{_safe_float(item.get('weight')):.2f}</td>"
            f"<td>{_safe_float(item.get('capital')):.2f} EUR</td>"
            f"<td>{_safe_float(item.get('learned_score')):.2f}</td>"
            "</tr>"
        )

    if not trading_plan_rows:
        trading_plan_rows = "<tr><td colspan='7'>Kein aktueller Trading-Plan verfügbar.</td></tr>"

    order_rows = ""
    for item in report["orders"]:
        order_rows += (
            "<tr>"
            f"<td>{item.get('action', '-')}</td>"
            f"<td>{item.get('symbol', '-')}</td>"
            f"<td>{_safe_text(item.get('reason_label'), item.get('reason', '-'))}</td>"
            f"<td>{_safe_float(item.get('capital')):.2f} EUR</td>"
            f"<td>{_safe_float(item.get('weight')):.2f}</td>"
            f"<td>{_safe_float(item.get('learned_score')):.2f}</td>"
            "</tr>"
        )

    if not order_rows:
        order_rows = "<tr><td colspan='6'>Keine aktuellen Orders verfügbar.</td></tr>"

    simulated_portfolio_rows = ""
    for item in report["simulated_portfolio"]:
        simulated_portfolio_rows += (
            "<tr>"
            f"<td>{item.get('symbol', '-')}</td>"
            f"<td>{item.get('isin', '-')}</td>"
            f"<td>{item.get('wkn', '-')}</td>"
            f"<td>{item.get('company', item.get('company_name', item.get('symbol', '-')))}</td>"
            f"<td>{_safe_float(item.get('qty')):.2f}</td>"
            f"<td>{_safe_float(item.get('price_eur')):.2f} EUR</td>"
            f"<td>{_safe_float(item.get('value_eur')):.2f} EUR</td>"
            "</tr>"
        )

    if not simulated_portfolio_rows:
        simulated_portfolio_rows = (
            "<tr><td colspan='7'>Kein simuliertes Depot aus dem aktuellen Lauf verfügbar.</td></tr>"
        )

    top_rows = ""
    for item in report["top_symbols"]:
        top_rows += (
            f"<tr>"
            f"<td>{item['symbol']}</td>"
            f"<td>{item.get('isin', '-')}</td>"
            f"<td>{item.get('wkn', '-')}</td>"
            f"<td>{item.get('company', item['symbol'])}</td>"
            f"<td>{item.get('count', 0)}</td>"
            f"</tr>"
        )

    if not top_rows:
        top_rows = "<tr><td colspan='5'>Keine Top-Aktien verfügbar.</td></tr>"

    result_explanations_html = _explanation_html(
        report["current_results"],
        "Keine aktuellen Analyse-Erklärungen verfügbar.",
    )
    candidate_explanations_html = _explanation_html(
        report["future_candidates"],
        "Keine Kandidaten-Erklärungen verfügbar.",
    )
    plan_explanations_html = _explanation_html(
        report["trading_plan"],
        "Keine Plan-Erklärungen verfügbar.",
    )
    order_explanations_html = _explanation_html(
        report["orders"],
        "Keine Order-Erklärungen verfügbar.",
    )

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>Daily Report</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 32px;
      background: #f5f7fb;
      color: #1f2937;
    }}
    .container {{
      max-width: 1100px;
      margin: 0 auto;
    }}
    .card {{
      background: white;
      border-radius: 14px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
      padding: 24px;
      margin-bottom: 20px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }}
    .kpi {{
      background: #f9fafb;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 16px;
    }}
    .label {{
      font-size: 13px;
      color: #6b7280;
      margin-bottom: 6px;
    }}
    .value {{
      font-size: 28px;
      font-weight: bold;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      text-align: left;
      padding: 10px 12px;
      border-bottom: 1px solid #e5e7eb;
    }}
    th {{
      color: #6b7280;
      font-size: 13px;
      text-transform: uppercase;
    }}
    .muted {{
      color: #6b7280;
    }}
    .explanations {{
      margin: 14px 0 0 18px;
      padding: 0;
    }}
    .explanations li {{
      margin: 0 0 10px 0;
    }}
    .explanation-meta {{
      color: #6b7280;
      font-size: 13px;
      margin-top: 4px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>Daily Report</h1>
      <p class="muted">Erstellt am: {report['generated_at']}</p>
      <p class="muted">Nur Simulation • Keine echten Orders • Keine Anlageberatung</p>
    </div>

    <div class="card">
      <h2>Aktueller Analyse-Lauf</h2>
      <p class="muted">Diese Werte stammen aus dem letzten frischen Analyse-Lauf und nicht aus dem historischen Journal.</p>
      <p><strong>Quelle:</strong> {report['analysis_source_label']}</p>
      <p><strong>Profil:</strong> {report['profile_name']}</p>
      <p><strong>Analyse-Zeitpunkt:</strong> {report['analysis_generated_at']}</p>
      <p><strong>Zeitraum:</strong> {report['analysis_period']} | <strong>Intervall:</strong> {report['analysis_interval']}</p>
      <p><strong>Ergebnisse:</strong> {report['analysis_result_count']} | <strong>Kandidaten:</strong> {report['analysis_candidate_count']} | <strong>Orders:</strong> {report['analysis_order_count']}</p>
    </div>

    <div class="card">
      <h2>Aktuelle Analyse-Ergebnisse</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>ISIN</th>
            <th>WKN</th>
            <th>Signal</th>
            <th>Firma</th>
            <th>P/L EUR</th>
            <th>Trades</th>
            <th>Score</th>
          </tr>
        </thead>
        <tbody>
          {current_result_rows}
        </tbody>
      </table>
      {result_explanations_html}
    </div>

    <div class="card">
      <h2>Aktuelle Kaufkandidaten</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>ISIN</th>
            <th>WKN</th>
            <th>Signal</th>
            <th>Firma</th>
            <th>Score</th>
            <th>Learned</th>
          </tr>
        </thead>
        <tbody>
          {candidate_rows}
        </tbody>
      </table>
      {candidate_explanations_html}
    </div>

    <div class="card">
      <h2>Aktueller Trading-Plan</h2>
      <p class="muted">Dieser Abschnitt zeigt die aktuelle Allokation aus dem letzten Analyse-Lauf.</p>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>ISIN</th>
            <th>WKN</th>
            <th>Firma</th>
            <th>Gewicht</th>
            <th>Kapital</th>
            <th>Learned</th>
          </tr>
        </thead>
        <tbody>
          {trading_plan_rows}
        </tbody>
      </table>
      {plan_explanations_html}
    </div>

    <div class="card">
      <h2>Aktuelle Orders</h2>
      <p class="muted">Order-Vorschlaege aus dem letzten Analyse-Lauf.</p>
      <table>
        <thead>
          <tr>
            <th>Aktion</th>
            <th>Symbol</th>
            <th>Grund</th>
            <th>Kapital</th>
            <th>Gewicht</th>
            <th>Learned</th>
          </tr>
        </thead>
        <tbody>
          {order_rows}
        </tbody>
      </table>
      {order_explanations_html}
    </div>

    <div class="card">
      <h2>Simuliertes Depot (aktueller Lauf)</h2>
      <p class="muted">Virtuelles Analyse-Depot aus dem letzten CLI-Lauf, getrennt vom persistierten Mini-System-State.</p>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>ISIN</th>
            <th>WKN</th>
            <th>Firma</th>
            <th>Qty</th>
            <th>Kurs EUR</th>
            <th>Wert EUR</th>
          </tr>
        </thead>
        <tbody>
          {simulated_portfolio_rows}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>Historische Performance</h2>
      <p class="muted">Diese Kennzahlen werden aus dem persistierten Journal und dem selbstlernenden Score abgeleitet.</p>
      <div class="grid">
        <div class="kpi"><div class="label">Journal-Einträge</div><div class="value">{report['total_entries']}</div></div>
        <div class="kpi"><div class="label">Aktien gesamt</div><div class="value">{report['stocks_total']}</div></div>
        <div class="kpi"><div class="label">Geschlossene Trades</div><div class="value">{report['closed_trades']}</div></div>
        <div class="kpi"><div class="label">Trefferquote</div><div class="value">{report['hit_rate']:.2f}%</div></div>
        <div class="kpi"><div class="label">BUY</div><div class="value">{report['buy_signals']}</div></div>
        <div class="kpi"><div class="label">SELL</div><div class="value">{report['sell_signals']}</div></div>
        <div class="kpi"><div class="label">WATCH</div><div class="value">{report['watch_signals']}</div></div>
        <div class="kpi"><div class="label">HOLD</div><div class="value">{report['hold_signals']}</div></div>
        <div class="kpi"><div class="label">Gewinntrades</div><div class="value">{report['winning_trades']}</div></div>
        <div class="kpi"><div class="label">Verlusttrades</div><div class="value">{report['losing_trades']}</div></div>
        <div class="kpi"><div class="label">Realisierter P/L</div><div class="value">{report['realized_pnl']:.2f} EUR</div></div>
        <div class="kpi"><div class="label">Ø Trade P/L</div><div class="value">{report['avg_trade']:.2f} EUR</div></div>
      </div>
    </div>

    <div class="card">
      <h2>Historische Top-Aktien</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>ISIN</th>
            <th>WKN</th>
            <th>Firma</th>
            <th>Häufigkeit</th>
          </tr>
        </thead>
        <tbody>
          {top_rows}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>Mini-System / Depot-State</h2>
      <p class="muted">Diese Werte kommen aus dem persistierten Zustandsfile des Mini-Systems.</p>
      <div class="grid">
        <div class="kpi"><div class="label">Cash</div><div class="value">{report['state_cash_eur']:.2f} EUR</div></div>
        <div class="kpi"><div class="label">Investiert</div><div class="value">{report['state_invested_eur']:.2f} EUR</div></div>
        <div class="kpi"><div class="label">Equity</div><div class="value">{report['state_equity_eur']:.2f} EUR</div></div>
        <div class="kpi"><div class="label">Peak Equity</div><div class="value">{report['state_peak_equity_eur']:.2f} EUR</div></div>
        <div class="kpi"><div class="label">Drawdown</div><div class="value">{report['state_drawdown_pct']:.2f}%</div></div>
        <div class="kpi"><div class="label">Offene Positionen</div><div class="value">{report['state_positions']}</div></div>
      </div>
      <p class="muted">State-Update: {report['state_updated_at']}</p>
    </div>

    <div class="card">
      <h2>Risikoprofil</h2>
      <p>Max Position: {report['risk_max_position_pct']:.0f}% | Stop-Loss: {report['risk_stop_loss_pct']:.0f}% | Trailing Stop: {report['risk_trailing_stop_pct']:.0f}% | Max Drawdown: {report['risk_max_drawdown_pct']:.0f}%</p>
    </div>
  </div>
</body>
</html>
"""


def _write_txt(report):
    with open(TXT_PATH, "w", encoding="utf-8") as f:
        f.write(_build_text_report(report))


def _write_html(report):
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(_build_html_report(report))


def _write_csv(report):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["key", "value"])

        for key in [
            "generated_at",
            "analysis_source",
            "analysis_source_label",
            "analysis_generated_at",
            "analysis_period",
            "analysis_interval",
            "analysis_result_count",
            "analysis_candidate_count",
            "analysis_order_count",
            "profile_name",
            "total_entries",
            "buy_signals",
            "sell_signals",
            "watch_signals",
            "hold_signals",
            "stocks_total",
            "closed_trades",
            "winning_trades",
            "losing_trades",
            "hit_rate",
            "realized_pnl",
            "avg_trade",
            "state_cash_eur",
            "state_invested_eur",
            "state_equity_eur",
            "state_peak_equity_eur",
            "state_drawdown_pct",
            "state_positions",
            "state_updated_at",
            "risk_max_position_pct",
            "risk_stop_loss_pct",
            "risk_trailing_stop_pct",
            "risk_max_drawdown_pct",
        ]:
            writer.writerow([key, report.get(key, "")])

        writer.writerow(["current_results_rows", len(report.get("current_results", []))])
        writer.writerow(["future_candidates_rows", len(report.get("future_candidates", []))])
        writer.writerow(["trading_plan_rows", len(report.get("trading_plan", []))])
        writer.writerow(["orders_rows", len(report.get("orders", []))])
        writer.writerow(["simulated_portfolio_rows", len(report.get("simulated_portfolio", []))])
        writer.writerow(["top_symbols_rows", len(report.get("top_symbols", []))])

        if "error" in report:
            writer.writerow(["error", report["error"]])


def _write_xml(report):
    root = ET.Element("daily_report")

    def _append_rows(parent_name, rows, fields):
        parent = ET.SubElement(root, parent_name)
        for item in rows:
            row = ET.SubElement(parent, "row")
            for field in fields:
                ET.SubElement(row, field).text = str(item.get(field, ""))

    for key, value in report.items():
        if key in {
            "top_symbols",
            "score_validation",
            "current_results",
            "future_candidates",
            "trading_plan",
            "simulated_portfolio",
            "orders",
        }:
            continue
        node = ET.SubElement(root, key)
        node.text = str(value)

    _append_rows(
        "current_results",
        report.get("current_results", []),
        ["symbol", "isin", "wkn", "signal", "company", "pnl_eur", "trade_count", "score", "explanation_summary"],
    )
    _append_rows(
        "future_candidates",
        report.get("future_candidates", []),
        ["symbol", "isin", "wkn", "future_signal", "company", "score", "learned_bonus", "explanation_summary"],
    )
    _append_rows(
        "trading_plan",
        report.get("trading_plan", []),
        ["symbol", "isin", "wkn", "company", "weight", "capital", "learned_score", "explanation_summary"],
    )
    _append_rows(
        "orders",
        report.get("orders", []),
        ["action", "symbol", "reason", "reason_label", "capital", "weight", "learned_score", "explanation_summary"],
    )
    _append_rows(
        "simulated_portfolio",
        report.get("simulated_portfolio", []),
        ["symbol", "isin", "wkn", "company", "qty", "price_eur", "value_eur"],
    )
    _append_rows(
        "top_symbols",
        report.get("top_symbols", []),
        ["symbol", "isin", "wkn", "company", "count"],
    )

    tree = ET.ElementTree(root)
    tree.write(XML_PATH, encoding="utf-8", xml_declaration=True)


def _draw_wrapped_text(pdf, text, x, y, max_width, font_name="Helvetica", font_size=11, line_gap=14):
    pdf.setFont(font_name, font_size)
    words = text.split()
    line = ""

    for word in words:
        candidate = f"{line} {word}".strip()
        if stringWidth(candidate, font_name, font_size) <= max_width:
            line = candidate
        else:
            pdf.drawString(x, y, line)
            y -= line_gap
            line = word

    if line:
        pdf.drawString(x, y, line)
        y -= line_gap

    return y


def _write_pdf(report):
    pdf = canvas.Canvas(PDF_PATH, pagesize=A4)
    width, height = A4
    x = 50
    y = height - 50
    max_width = width - 100

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(x, y, "Daily Report")
    y -= 24

    pdf.setFont("Helvetica", 10)
    pdf.drawString(x, y, f"Erstellt am: {report['generated_at']}")
    y -= 24

    if "error" in report:
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(x, y, "Fehler")
        y -= 18
        y = _draw_wrapped_text(pdf, report["error"], x, y, max_width)
        pdf.save()
        return

    def _ensure_space(lines=3):
        nonlocal y
        if y < 60 + (lines * 14):
            pdf.showPage()
            y = height - 50

    def _section(title):
        nonlocal y
        _ensure_space(3)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(x, y, title)
        y -= 18

    def _kv_lines(entries):
        nonlocal y
        pdf.setFont("Helvetica", 11)
        for label, value in entries:
            _ensure_space(2)
            pdf.drawString(x, y, f"{label}:")
            y = _draw_wrapped_text(pdf, str(value), x + 180, y, max_width - 180)

    def _wrapped_lines(lines, empty_message):
        nonlocal y
        pdf.setFont("Helvetica", 11)
        if not lines:
            _ensure_space(2)
            pdf.drawString(x, y, empty_message)
            y -= 16
            return
        for line in lines:
            _ensure_space(2)
            y = _draw_wrapped_text(pdf, line, x, y, max_width)

    _section("Aktueller Analyse-Lauf")
    _kv_lines(
        [
            ("Quelle", report["analysis_source_label"]),
            ("Profil", report["profile_name"]),
            ("Analyse-Zeitpunkt", report["analysis_generated_at"]),
            ("Zeitraum", report["analysis_period"]),
            ("Intervall", report["analysis_interval"]),
            ("Analyse-Ergebnisse", report["analysis_result_count"]),
            ("Aktuelle Kandidaten", report["analysis_candidate_count"]),
            ("Aktuelle Orders", report["analysis_order_count"]),
        ]
    )

    _section("Aktuelle Analyse-Ergebnisse")
    _wrapped_lines(
        [
            (
                f"{item.get('symbol', '-')} | ISIN {item.get('isin', '-')} | WKN {item.get('wkn', '-')} | "
                f"Signal {item.get('signal', '-')} | P/L { _safe_float(item.get('pnl_eur')):.2f} EUR | "
                f"Trades {int(item.get('trade_count', 0))} | Score { _safe_float(item.get('score')):.2f}"
            )
            for item in report.get("current_results", [])
        ],
        "Keine frischen Analyse-Ergebnisse verfügbar.",
    )
    _section("Warum diese Analyse-Ergebnisse")
    _wrapped_lines(
        _explanation_pdf_lines(report.get("current_results", [])),
        "Keine aktuellen Analyse-Erklärungen verfügbar.",
    )

    _section("Aktuelle Kaufkandidaten")
    _wrapped_lines(
        [
            (
                f"{item.get('symbol', '-')} | ISIN {item.get('isin', '-')} | WKN {item.get('wkn', '-')} | "
                f"Signal {item.get('future_signal', '-')} | Score { _safe_float(item.get('score')):.2f} | "
                f"Learned { _safe_float(item.get('learned_bonus')):+.2f} | "
                f"{item.get('company', item.get('company_name', item.get('symbol', '-')))}"
            )
            for item in report.get("future_candidates", [])
        ],
        "Keine aktuellen Kaufkandidaten verfügbar.",
    )
    _section("Warum diese Kandidaten")
    _wrapped_lines(
        _explanation_pdf_lines(report.get("future_candidates", [])),
        "Keine Kandidaten-Erklärungen verfügbar.",
    )

    _section("Aktueller Trading-Plan")
    _wrapped_lines(
        [
            (
                f"{item.get('symbol', '-')} | ISIN {item.get('isin', '-')} | WKN {item.get('wkn', '-')} | "
                f"Gewicht { _safe_float(item.get('weight')):.2f} | Kapital { _safe_float(item.get('capital')):.2f} EUR | "
                f"Learned { _safe_float(item.get('learned_score')):.2f} | "
                f"{item.get('company', item.get('company_name', item.get('symbol', '-')))}"
            )
            for item in report.get("trading_plan", [])
        ],
        "Kein aktueller Trading-Plan verfügbar.",
    )
    _section("Warum dieser Trading-Plan")
    _wrapped_lines(
        _explanation_pdf_lines(report.get("trading_plan", [])),
        "Keine Plan-Erklärungen verfügbar.",
    )

    _section("Aktuelle Orders")
    _wrapped_lines(
        [
            (
                f"{item.get('action', '-')} {item.get('symbol', '-')} | "
                f"Grund {_safe_text(item.get('reason_label'), item.get('reason', '-'))} | Kapital { _safe_float(item.get('capital')):.2f} EUR | "
                f"Gewicht { _safe_float(item.get('weight')):.2f} | "
                f"Learned { _safe_float(item.get('learned_score')):.2f}"
            )
            for item in report.get("orders", [])
        ],
        "Keine aktuellen Orders verfügbar.",
    )
    _section("Warum diese Orders")
    _wrapped_lines(
        _explanation_pdf_lines(report.get("orders", [])),
        "Keine Order-Erklärungen verfügbar.",
    )

    _section("Simuliertes Depot (aktueller Lauf)")
    _wrapped_lines(
        [
            (
                f"{item.get('symbol', '-')} | ISIN {item.get('isin', '-')} | WKN {item.get('wkn', '-')} | "
                f"Qty { _safe_float(item.get('qty')):.2f} | Kurs { _safe_float(item.get('price_eur')):.2f} EUR | "
                f"Wert { _safe_float(item.get('value_eur')):.2f} EUR | "
                f"{item.get('company', item.get('company_name', item.get('symbol', '-')))}"
            )
            for item in report.get("simulated_portfolio", [])
        ],
        "Kein simuliertes Depot aus dem aktuellen Lauf verfügbar.",
    )

    _section("Historische Performance")
    _kv_lines(
        [
            ("Journal-Einträge", report["total_entries"]),
            ("BUY Signale", report["buy_signals"]),
            ("SELL Signale", report["sell_signals"]),
            ("WATCH Signale", report["watch_signals"]),
            ("HOLD Signale", report["hold_signals"]),
            ("Aktien gesamt", report["stocks_total"]),
            ("Geschlossene Trades", report["closed_trades"]),
            ("Gewinntrades", report["winning_trades"]),
            ("Verlusttrades", report["losing_trades"]),
            ("Trefferquote", f"{report['hit_rate']:.2f} %"),
            ("Realisierter P/L", f"{report['realized_pnl']:.2f} EUR"),
            ("Ø Trade P/L", f"{report['avg_trade']:.2f} EUR"),
        ]
    )

    _section("Historische Top-Aktien")
    _wrapped_lines(
        [
            (
                f"{item.get('symbol', '-')} ({item.get('company', item.get('symbol', '-'))}) | "
                f"ISIN: {item.get('isin', '-')} | WKN: {item.get('wkn', '-')} | "
                f"Anzahl: {item.get('count', 0)}"
            )
            for item in report.get("top_symbols", [])
        ],
        "Keine Top-Aktien verfügbar.",
    )

    _section("Mini-System / Depot-State")
    _kv_lines(
        [
            ("Cash", f"{report['state_cash_eur']:.2f} EUR"),
            ("Investiert", f"{report['state_invested_eur']:.2f} EUR"),
            ("Equity", f"{report['state_equity_eur']:.2f} EUR"),
            ("Peak Equity", f"{report['state_peak_equity_eur']:.2f} EUR"),
            ("Drawdown", f"{report['state_drawdown_pct']:.2f} %"),
            ("Offene Positionen", report["state_positions"]),
            ("State-Update", report["state_updated_at"]),
        ]
    )

    _section("Risikoprofil")
    _kv_lines(
        [
            ("Max Position", f"{report['risk_max_position_pct']:.0f} %"),
            ("Stop-Loss", f"{report['risk_stop_loss_pct']:.0f} %"),
            ("Trailing Stop", f"{report['risk_trailing_stop_pct']:.0f} %"),
            ("Max Drawdown", f"{report['risk_max_drawdown_pct']:.0f} %"),
        ]
    )

    pdf.save()


def create_daily_report():
    _ensure_reports_dir()

    report = _build_report_data()

    _write_txt(report)
    _write_html(report)
    _write_csv(report)
    _write_xml(report)
    _write_pdf(report)

    if "error" in report:
        print(f"Daily Report erstellt, aber mit Fehlerstatus: {report['error']}")
        return report

    print("Daily Report erfolgreich erstellt.")
    return report


if __name__ == "__main__":
    create_daily_report()
