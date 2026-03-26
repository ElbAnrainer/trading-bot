from datetime import datetime
from pathlib import Path
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom

from performance import analyze_performance
from score_learning import load_learning_model
from data_loader import load_ticker_metadata


REPORTS_DIR = Path("reports")
DAILY_REPORTS_DIR = REPORTS_DIR / "daily_reports"


def _ensure_dirs():
    DAILY_REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _company_name(symbol, cache):
    if symbol not in cache:
        try:
            meta = load_ticker_metadata(symbol)
            cache[symbol] = meta.get("name", symbol)
        except Exception:
            cache[symbol] = symbol
    return cache[symbol]


def _format_symbol(symbol, cache):
    return f"{symbol} ({_company_name(symbol, cache)})"


def _build_report_data():
    stats = analyze_performance()
    learning_model = load_learning_model()
    now = datetime.now()
    name_cache = {}

    report = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "simulation_only": True,
        "summary": {},
        "top_symbols": [],
        "per_symbol_performance": [],
        "score_validation": [],
        "learning_model": [],
        "conclusion": [],
    }

    if not stats:
        report["summary"] = {
            "message": "Keine Simulationsdaten vorhanden."
        }
        report["conclusion"] = ["Keine Simulationsdaten vorhanden."]
        return report

    report["summary"] = {
        "total_entries": stats["total_entries"],
        "buy_count": stats["buy_count"],
        "sell_count": stats["sell_count"],
        "watch_count": stats["watch_count"],
        "hold_count": stats["hold_count"],
        "unique_symbols": stats["unique_symbols"],
        "closed_trades": stats["closed_trades"],
        "win_trades": stats["win_trades"],
        "loss_trades": stats["loss_trades"],
        "hit_rate_pct": round(stats["hit_rate_pct"], 2),
        "realized_pnl_eur": round(stats["realized_pnl_eur"], 2),
        "avg_trade_pnl_eur": round(stats["avg_trade_pnl_eur"], 2),
    }

    for sym, count in stats["top_symbols"]:
        report["top_symbols"].append({
            "symbol": sym,
            "company_name": _company_name(sym, name_cache),
            "count": count,
        })

    ranked_performance = sorted(
        stats["per_symbol"].items(),
        key=lambda x: x[1]["pnl"],
        reverse=True,
    )
    for sym, data in ranked_performance:
        report["per_symbol_performance"].append({
            "symbol": sym,
            "company_name": _company_name(sym, name_cache),
            "trades": data["trades"],
            "pnl_eur": round(data["pnl"], 2),
            "avg_trade_pnl_eur": round(data["avg"], 2),
            "hit_rate_pct": round(data["hit"], 2),
            "score": round(data.get("score", 0.0), 2),
        })

    ranked_score = sorted(
        stats["score_validation"],
        key=lambda x: x["score"],
        reverse=True,
    )
    for item in ranked_score:
        report["score_validation"].append({
            "symbol": item["symbol"],
            "company_name": _company_name(item["symbol"], name_cache),
            "score": round(item["score"], 2),
            "pnl_eur": round(item["pnl"], 2),
            "trades": item["trades"],
            "hit_rate_pct": round(item["hit"], 2),
        })

    if learning_model:
        ranked_learning = sorted(
            learning_model.items(),
            key=lambda x: x[1].get("learned_bonus", 0.0),
            reverse=True,
        )
        for sym, data in ranked_learning:
            report["learning_model"].append({
                "symbol": sym,
                "company_name": _company_name(sym, name_cache),
                "learned_bonus": round(data["learned_bonus"], 2),
                "hit_rate_pct": round(data["hit_rate"], 2),
                "avg_pnl_eur": round(data["avg_pnl"], 2),
                "trades": data["trades"],
                "confidence": round(data["confidence"], 2),
            })

    if stats["realized_pnl_eur"] > 0:
        report["conclusion"].append("Die Simulation ist aktuell profitabel.")
    elif stats["realized_pnl_eur"] < 0:
        report["conclusion"].append("Die Simulation ist aktuell negativ und sollte überprüft werden.")
    else:
        report["conclusion"].append("Die Simulation ist aktuell neutral.")

    if stats["hit_rate_pct"] >= 55:
        report["conclusion"].append("Die Trefferquote wirkt solide.")
    elif stats["hit_rate_pct"] >= 45:
        report["conclusion"].append("Die Trefferquote ist mittelmäßig und sollte beobachtet werden.")
    else:
        report["conclusion"].append("Die Trefferquote ist schwach und sollte verbessert werden.")

    return report


def _build_text_report(report):
    lines = []
    lines.append("DAILY REPORT")
    lines.append("=" * 72)
    lines.append(f"Erstellt am: {report['generated_at']}")
    lines.append("Hinweis: Nur Simulation, keine echten Orders, keine Anlageberatung.")
    lines.append("")

    summary = report.get("summary", {})
    if summary.get("message"):
        lines.append(summary["message"])
        lines.append("")
        return "\n".join(lines)

    lines.append("UEBERSICHT")
    lines.append("-" * 72)
    lines.append(f"Journal-Einträge     : {summary['total_entries']}")
    lines.append(f"BUY Signale          : {summary['buy_count']}")
    lines.append(f"SELL Signale         : {summary['sell_count']}")
    lines.append(f"WATCH Signale        : {summary['watch_count']}")
    lines.append(f"HOLD Signale         : {summary['hold_count']}")
    lines.append(f"Aktien gesamt        : {summary['unique_symbols']}")
    lines.append(f"Geschlossene Trades  : {summary['closed_trades']}")
    lines.append(f"Gewinntrades         : {summary['win_trades']}")
    lines.append(f"Verlusttrades        : {summary['loss_trades']}")
    lines.append(f"Trefferquote         : {summary['hit_rate_pct']:.2f} %")
    lines.append(f"Realisierter P/L     : {summary['realized_pnl_eur']:.2f} EUR")
    lines.append(f"Ø Trade P/L          : {summary['avg_trade_pnl_eur']:.2f} EUR")
    lines.append("")

    lines.append("TOP AKTIEN NACH HAEUFIGKEIT")
    lines.append("-" * 72)
    if report["top_symbols"]:
        for item in report["top_symbols"]:
            lines.append(f"{item['symbol']} ({item['company_name']}): {item['count']}")
    else:
        lines.append("Keine Daten")
    lines.append("")

    lines.append("PERFORMANCE JE AKTIE")
    lines.append("-" * 72)
    if report["per_symbol_performance"]:
        for item in report["per_symbol_performance"][:10]:
            lines.append(f"{item['symbol']} ({item['company_name']})")
            lines.append(
                f"  Trades: {item['trades']} | "
                f"P/L: {item['pnl_eur']:.2f} EUR | "
                f"Ø: {item['avg_trade_pnl_eur']:.2f} EUR | "
                f"Treffer: {item['hit_rate_pct']:.1f}% | "
                f"Score: {item['score']:.1f}"
            )
    else:
        lines.append("Keine Performance-Daten")
    lines.append("")

    lines.append("SCORE-VALIDIERUNG")
    lines.append("-" * 72)
    if report["score_validation"]:
        for item in report["score_validation"][:10]:
            lines.append(f"{item['symbol']} ({item['company_name']})")
            lines.append(
                f"  Score: {item['score']:.1f} | "
                f"P/L: {item['pnl_eur']:.2f} EUR | "
                f"Trades: {item['trades']} | "
                f"Treffer: {item['hit_rate_pct']:.1f}%"
            )
    else:
        lines.append("Keine Score-Validierung verfügbar")
    lines.append("")

    lines.append("SELBSTLERNENDER SCORE")
    lines.append("-" * 72)
    if report["learning_model"]:
        for item in report["learning_model"][:10]:
            lines.append(f"{item['symbol']} ({item['company_name']})")
            lines.append(
                f"  Lernbonus: {item['learned_bonus']:+.2f} | "
                f"Treffer: {item['hit_rate_pct']:.1f}% | "
                f"Ø P/L: {item['avg_pnl_eur']:.2f} EUR | "
                f"Trades: {item['trades']} | "
                f"Confidence: {item['confidence']:.2f}"
            )
    else:
        lines.append("Noch nicht genug Historie für Lernbonus.")
    lines.append("")

    lines.append("FAZIT")
    lines.append("-" * 72)
    for item in report["conclusion"]:
        lines.append(item)

    lines.append("")
    lines.append("Ende des Reports.")
    lines.append("")

    return "\n".join(lines)


def _build_html_report(text_report):
    escaped = (
        text_report.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
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
            background: #f7f7f7;
            color: #222;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        h1 {{
            margin-top: 0;
        }}
        pre {{
            white-space: pre-wrap;
            font-family: "SFMono-Regular", Consolas, monospace;
            font-size: 14px;
            line-height: 1.45;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Daily Report</h1>
        <p>Nur Simulation, keine echten Orders, keine Anlageberatung.</p>
        <pre>{escaped}</pre>
    </div>
</body>
</html>
"""


def _write_pdf_report(text_report, pdf_path):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
        from reportlab.lib import colors
    except ImportError:
        print("PDF-Erzeugung übersprungen: reportlab ist nicht installiert.")
        return False

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    mono_style = ParagraphStyle(
        "MonoStyle",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=8.5,
        leading=11,
        backColor=colors.whitesmoke,
        leftIndent=6,
        rightIndent=6,
        spaceBefore=4,
        spaceAfter=8,
    )

    story = []
    story.append(Paragraph("Daily Report", title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Nur Simulation, keine echten Orders, keine Anlageberatung.", body_style))
    story.append(Spacer(1, 10))

    sections = text_report.split("\n\n")
    first_block = True

    for block in sections:
        block = block.strip()
        if not block:
            continue

        lines = block.splitlines()
        if not lines:
            continue

        if first_block:
            story.append(Preformatted("\n".join(lines), mono_style))
            first_block = False
            continue

        if len(lines) >= 2 and set(lines[1]) == {"-"}:
            story.append(Paragraph(lines[0], heading_style))
            content = "\n".join(lines[2:]).strip()
            if content:
                story.append(Preformatted(content, mono_style))
            story.append(Spacer(1, 6))
        else:
            story.append(Preformatted("\n".join(lines), mono_style))
            story.append(Spacer(1, 6))

    doc.build(story)
    return True


def _write_csv_report(report, csv_path):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["section", "symbol", "company_name", "metric", "value"])

        for key, value in report.get("summary", {}).items():
            writer.writerow(["summary", "", "", key, value])

        for item in report.get("top_symbols", []):
            writer.writerow(["top_symbols", item["symbol"], item["company_name"], "count", item["count"]])

        for item in report.get("per_symbol_performance", []):
            writer.writerow(["per_symbol_performance", item["symbol"], item["company_name"], "trades", item["trades"]])
            writer.writerow(["per_symbol_performance", item["symbol"], item["company_name"], "pnl_eur", item["pnl_eur"]])
            writer.writerow(["per_symbol_performance", item["symbol"], item["company_name"], "avg_trade_pnl_eur", item["avg_trade_pnl_eur"]])
            writer.writerow(["per_symbol_performance", item["symbol"], item["company_name"], "hit_rate_pct", item["hit_rate_pct"]])
            writer.writerow(["per_symbol_performance", item["symbol"], item["company_name"], "score", item["score"]])

        for item in report.get("score_validation", []):
            writer.writerow(["score_validation", item["symbol"], item["company_name"], "score", item["score"]])
            writer.writerow(["score_validation", item["symbol"], item["company_name"], "pnl_eur", item["pnl_eur"]])
            writer.writerow(["score_validation", item["symbol"], item["company_name"], "trades", item["trades"]])
            writer.writerow(["score_validation", item["symbol"], item["company_name"], "hit_rate_pct", item["hit_rate_pct"]])

        for item in report.get("learning_model", []):
            writer.writerow(["learning_model", item["symbol"], item["company_name"], "learned_bonus", item["learned_bonus"]])
            writer.writerow(["learning_model", item["symbol"], item["company_name"], "hit_rate_pct", item["hit_rate_pct"]])
            writer.writerow(["learning_model", item["symbol"], item["company_name"], "avg_pnl_eur", item["avg_pnl_eur"]])
            writer.writerow(["learning_model", item["symbol"], item["company_name"], "trades", item["trades"]])
            writer.writerow(["learning_model", item["symbol"], item["company_name"], "confidence", item["confidence"]])

        for item in report.get("conclusion", []):
            writer.writerow(["conclusion", "", "", "text", item])


def _indent_xml(elem):
    rough = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8")


def _write_xml_report(report, xml_path):
    root = ET.Element("daily_report")
    root.set("generated_at", report.get("generated_at", ""))
    root.set("simulation_only", str(report.get("simulation_only", True)).lower())

    summary = ET.SubElement(root, "summary")
    for key, value in report.get("summary", {}).items():
        elem = ET.SubElement(summary, key)
        elem.text = str(value)

    top_symbols = ET.SubElement(root, "top_symbols")
    for item in report.get("top_symbols", []):
        entry = ET.SubElement(top_symbols, "symbol")
        entry.set("ticker", str(item["symbol"]))
        entry.set("company_name", str(item["company_name"]))
        entry.set("count", str(item["count"]))

    performance = ET.SubElement(root, "per_symbol_performance")
    for item in report.get("per_symbol_performance", []):
        entry = ET.SubElement(performance, "symbol")
        entry.set("ticker", str(item["symbol"]))
        entry.set("company_name", str(item["company_name"]))
        for key in ("trades", "pnl_eur", "avg_trade_pnl_eur", "hit_rate_pct", "score"):
            child = ET.SubElement(entry, key)
            child.text = str(item[key])

    score_validation = ET.SubElement(root, "score_validation")
    for item in report.get("score_validation", []):
        entry = ET.SubElement(score_validation, "symbol")
        entry.set("ticker", str(item["symbol"]))
        entry.set("company_name", str(item["company_name"]))
        for key in ("score", "pnl_eur", "trades", "hit_rate_pct"):
            child = ET.SubElement(entry, key)
            child.text = str(item[key])

    learning_model = ET.SubElement(root, "learning_model")
    for item in report.get("learning_model", []):
        entry = ET.SubElement(learning_model, "symbol")
        entry.set("ticker", str(item["symbol"]))
        entry.set("company_name", str(item["company_name"]))
        for key in ("learned_bonus", "hit_rate_pct", "avg_pnl_eur", "trades", "confidence"):
            child = ET.SubElement(entry, key)
            child.text = str(item[key])

    conclusion = ET.SubElement(root, "conclusion")
    for item in report.get("conclusion", []):
        child = ET.SubElement(conclusion, "item")
        child.text = str(item)

    xml_bytes = _indent_xml(root)
    with open(xml_path, "wb") as f:
        f.write(xml_bytes)


def create_daily_report():
    _ensure_dirs()

    report = _build_report_data()
    report_text = _build_text_report(report)
    report_html = _build_html_report(report_text)

    today = datetime.now().strftime("%Y-%m-%d")

    text_path = DAILY_REPORTS_DIR / f"daily_report_{today}.txt"
    html_path = DAILY_REPORTS_DIR / f"daily_report_{today}.html"
    pdf_path = DAILY_REPORTS_DIR / f"daily_report_{today}.pdf"
    csv_path = DAILY_REPORTS_DIR / f"daily_report_{today}.csv"
    xml_path = DAILY_REPORTS_DIR / f"daily_report_{today}.xml"

    latest_text = REPORTS_DIR / "daily_report_latest.txt"
    latest_html = REPORTS_DIR / "daily_report_latest.html"
    latest_pdf = REPORTS_DIR / "daily_report_latest.pdf"
    latest_csv = REPORTS_DIR / "daily_report_latest.csv"
    latest_xml = REPORTS_DIR / "daily_report_latest.xml"

    text_path.write_text(report_text, encoding="utf-8")
    html_path.write_text(report_html, encoding="utf-8")
    latest_text.write_text(report_text, encoding="utf-8")
    latest_html.write_text(report_html, encoding="utf-8")

    _write_csv_report(report, csv_path)
    _write_csv_report(report, latest_csv)
    _write_xml_report(report, xml_path)
    _write_xml_report(report, latest_xml)

    pdf_created = _write_pdf_report(report_text, pdf_path)
    if pdf_created:
        _write_pdf_report(report_text, latest_pdf)

    print(f"Daily Report gespeichert: {text_path}")
    print(f"Daily Report HTML gespeichert: {html_path}")
    print(f"Daily Report CSV gespeichert: {csv_path}")
    print(f"Daily Report XML gespeichert: {xml_path}")
    if pdf_created:
        print(f"Daily Report PDF gespeichert: {pdf_path}")
    print(f"Latest TXT aktualisiert: {latest_text}")
    print(f"Latest HTML aktualisiert: {latest_html}")
    print(f"Latest CSV aktualisiert: {latest_csv}")
    print(f"Latest XML aktualisiert: {latest_xml}")
    if pdf_created:
        print(f"Latest PDF aktualisiert: {latest_pdf}")


if __name__ == "__main__":
    create_daily_report()
