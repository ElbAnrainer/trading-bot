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
from performance import analyze_performance


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


def _build_report_data():
    try:
        stats = analyze_performance()
    except Exception as exc:
        return {
            "error": f"Performance konnte nicht geladen werden: {exc}",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "top_symbols": [],
        }

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_entries": _safe_get(stats, "total_entries", _safe_get(stats, "journal_entries", 0)),
        "buy_signals": _safe_get(stats, "buy_signals", 0),
        "sell_signals": _safe_get(stats, "sell_signals", 0),
        "watch_signals": _safe_get(stats, "watch_signals", 0),
        "hold_signals": _safe_get(stats, "hold_signals", 0),
        "stocks_total": _safe_get(stats, "stocks_total", _safe_get(stats, "unique_symbols", 0)),
        "closed_trades": _safe_get(stats, "closed_trades_count", _safe_get(stats, "closed_trades", 0)),
        "winning_trades": _safe_get(stats, "winning_trades_count", _safe_get(stats, "winning_trades", 0)),
        "losing_trades": _safe_get(stats, "losing_trades_count", _safe_get(stats, "losing_trades", 0)),
        "hit_rate": _safe_get(stats, "hit_rate_pct", _safe_get(stats, "hit_rate", 0.0)),
        "realized_pnl": _safe_get(stats, "realized_pnl_eur", _safe_get(stats, "realized_pnl", 0.0)),
        "avg_trade": _safe_get(stats, "avg_trade_pnl_eur", _safe_get(stats, "avg_trade_pnl", 0.0)),
        "top_symbols": stats.get("top_symbols", []),
        "score_validation": stats.get("score_validation", []),
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

    lines.extend(
        [
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
            "",
            "TOP AKTIEN",
            "----------------------------------------",
        ]
    )

    if report["top_symbols"]:
        for item in report["top_symbols"]:
            lines.append(
                f"{item['symbol']} ({item.get('company', item['symbol'])}) | "
                f"ISIN: {item.get('isin', '-')} | WKN: {item.get('wkn', '-')} | "
                f"Anzahl: {item.get('count', 0)}"
            )
    else:
        lines.append("Keine Top-Aktien verfügbar.")

    lines.extend(
        [
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
      <h2>Kennzahlen</h2>
      <div class="grid">
        <div class="kpi"><div class="label">Journal-Einträge</div><div class="value">{report['total_entries']}</div></div>
        <div class="kpi"><div class="label">Geschlossene Trades</div><div class="value">{report['closed_trades']}</div></div>
        <div class="kpi"><div class="label">Trefferquote</div><div class="value">{report['hit_rate']:.2f}%</div></div>
        <div class="kpi"><div class="label">BUY</div><div class="value">{report['buy_signals']}</div></div>
        <div class="kpi"><div class="label">SELL</div><div class="value">{report['sell_signals']}</div></div>
        <div class="kpi"><div class="label">Realisierter P/L</div><div class="value">{report['realized_pnl']:.2f} EUR</div></div>
      </div>
    </div>

    <div class="card">
      <h2>Top-Aktien</h2>
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
        ]:
            writer.writerow([key, report.get(key, "")])

        if "error" in report:
            writer.writerow(["error", report["error"]])


def _write_xml(report):
    root = ET.Element("daily_report")

    for key, value in report.items():
        if key in {"top_symbols", "score_validation"}:
            continue
        node = ET.SubElement(root, key)
        node.text = str(value)

    top_symbols = ET.SubElement(root, "top_symbols")
    for item in report.get("top_symbols", []):
        sym = ET.SubElement(top_symbols, "symbol")
        ET.SubElement(sym, "ticker").text = str(item.get("symbol", ""))
        ET.SubElement(sym, "isin").text = str(item.get("isin", "-"))
        ET.SubElement(sym, "wkn").text = str(item.get("wkn", "-"))
        ET.SubElement(sym, "company").text = str(item.get("company", ""))
        ET.SubElement(sym, "count").text = str(item.get("count", 0))

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

    entries = [
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

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x, y, "Kennzahlen")
    y -= 18

    pdf.setFont("Helvetica", 11)
    for label, value in entries:
        pdf.drawString(x, y, f"{label}:")
        pdf.drawString(x + 180, y, str(value))
        y -= 16
        if y < 100:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 11)

    y -= 8
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x, y, "Top-Aktien")
    y -= 18

    pdf.setFont("Helvetica", 11)
    if report.get("top_symbols"):
        for item in report["top_symbols"]:
            line = (
                f"{item['symbol']} ({item.get('company', item['symbol'])}) | "
                f"ISIN: {item.get('isin', '-')} | WKN: {item.get('wkn', '-')} | "
                f"Anzahl: {item.get('count', 0)}"
            )
            y = _draw_wrapped_text(pdf, line, x, y, max_width)
            if y < 100:
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica", 11)
    else:
        pdf.drawString(x, y, "Keine Top-Aktien verfügbar.")
        y -= 16

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
