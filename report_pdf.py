import csv
import os
import shutil
from datetime import datetime
from statistics import mean, pstdev

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


REPORT_PATH_CANDIDATES = [
    "reports/trading_journal.csv",
    "trading_journal.csv",
]

REPORTS_DIR = "reports"
LATEST_PDF_PATH = os.path.join(REPORTS_DIR, "trading_report_latest.pdf")
CHART_EQUITY_PATH = os.path.join(REPORTS_DIR, "equity_curve.png")
CHART_TOP_SYMBOLS_PATH = os.path.join(REPORTS_DIR, "top_symbols.png")
MAX_VERSIONED_REPORTS = 100


def _build_output_path():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join(REPORTS_DIR, f"trading_report_{timestamp}.pdf")


def _find_report_path():
    for path in REPORT_PATH_CANDIDATES:
        if os.path.exists(path):
            return path
    return REPORT_PATH_CANDIDATES[0]


def _to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _ensure_reports_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)


def _copy_to_latest(versioned_pdf_path):
    shutil.copyfile(versioned_pdf_path, LATEST_PDF_PATH)


def _cleanup_old_reports(max_keep=MAX_VERSIONED_REPORTS):
    if not os.path.isdir(REPORTS_DIR):
        return

    files = []
    for name in os.listdir(REPORTS_DIR):
        if not name.startswith("trading_report_") or not name.endswith(".pdf"):
            continue
        if name == "trading_report_latest.pdf":
            continue
        files.append(os.path.join(REPORTS_DIR, name))

    files.sort(key=os.path.getmtime, reverse=True)

    if len(files) <= max_keep:
        return

    for old_file in files[max_keep:]:
        try:
            os.remove(old_file)
            print(f"Alte PDF gelöscht: {old_file}")
        except OSError as exc:
            print(f"Konnte alte PDF nicht löschen: {old_file} ({exc})")


def load_trades():
    report_path = _find_report_path()
    if not os.path.exists(report_path):
        return []

    trades = []
    with open(report_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            closed_trade = str(row.get("closed_trade", "")).strip().lower() == "true"
            if not closed_trade:
                continue

            pnl = _to_float(
                row.get("realized_pnl_eur", row.get("pnl_eur", 0.0)),
                0.0,
            )

            trades.append(
                {
                    "symbol": row.get("symbol", "").strip(),
                    "company": row.get("company", "").strip(),
                    "score": _to_float(row.get("score", 0.0), 0.0),
                    "pnl_eur": pnl,
                    "time": row.get("timestamp") or row.get("time") or "",
                }
            )
    return trades


def build_equity_curve(trades, initial_capital=10_000.0):
    equity = []
    value = initial_capital

    for trade in trades:
        value += trade["pnl_eur"]
        equity.append(value)

    return equity


def calculate_max_drawdown_pct(equity_curve):
    if not equity_curve:
        return 0.0

    peak = equity_curve[0]
    max_drawdown = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = ((peak - value) / peak) * 100.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

    return max_drawdown


def summarize_top_symbols(trades, top_n=5):
    by_symbol = {}

    for trade in trades:
        symbol = trade["symbol"] or "-"
        if symbol not in by_symbol:
            by_symbol[symbol] = {
                "company": trade["company"] or symbol,
                "trades": 0,
                "pnl": 0.0,
                "scores": [],
                "wins": 0,
                "losses": 0,
            }

        by_symbol[symbol]["trades"] += 1
        by_symbol[symbol]["pnl"] += trade["pnl_eur"]

        if trade["score"]:
            by_symbol[symbol]["scores"].append(trade["score"])

        if trade["pnl_eur"] > 0:
            by_symbol[symbol]["wins"] += 1
        elif trade["pnl_eur"] < 0:
            by_symbol[symbol]["losses"] += 1

    ranked = sorted(by_symbol.items(), key=lambda x: x[1]["pnl"], reverse=True)

    rows = []
    for symbol, data in ranked[:top_n]:
        avg_score = mean(data["scores"]) if data["scores"] else 0.0
        hit_rate = (data["wins"] / data["trades"] * 100.0) if data["trades"] else 0.0
        rows.append(
            {
                "symbol": symbol,
                "company": data["company"],
                "trades": data["trades"],
                "pnl": data["pnl"],
                "avg_score": avg_score,
                "hit_rate": hit_rate,
            }
        )
    return rows


def calculate_metrics(trades, initial_capital=10_000.0):
    if not trades:
        return {
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "avg_pnl": 0.0,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "sharpe": 0.0,
            "max_drawdown_pct": 0.0,
            "expectancy": 0.0,
            "final_equity": initial_capital,
            "best_trade": 0.0,
            "worst_trade": 0.0,
        }

    pnls = [t["pnl_eur"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    total = len(pnls)

    avg_pnl = mean(pnls) if pnls else 0.0
    win_rate = (len(wins) / total * 100.0) if total else 0.0

    volatility = pstdev(pnls) if len(pnls) > 1 else 0.0
    sharpe = (avg_pnl / volatility) if volatility > 0 else 0.0

    avg_win = mean(wins) if wins else 0.0
    avg_loss_abs = abs(mean(losses)) if losses else 0.0
    loss_rate = (len(losses) / total) if total else 0.0
    expectancy = ((len(wins) / total) * avg_win - loss_rate * avg_loss_abs) if total else 0.0

    equity_curve = build_equity_curve(trades, initial_capital=initial_capital)
    max_drawdown_pct = calculate_max_drawdown_pct(equity_curve)

    return {
        "total_pnl": sum(pnls),
        "win_rate": win_rate,
        "avg_pnl": avg_pnl,
        "trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "sharpe": sharpe,
        "max_drawdown_pct": max_drawdown_pct,
        "expectancy": expectancy,
        "final_equity": equity_curve[-1] if equity_curve else initial_capital,
        "best_trade": max(pnls) if pnls else 0.0,
        "worst_trade": min(pnls) if pnls else 0.0,
    }


def create_equity_chart(equity):
    if not equity:
        return None

    _ensure_reports_dir()

    plt.figure(figsize=(8.6, 4.8))
    plt.plot(equity, linewidth=2)
    plt.title("Equity Curve")
    plt.xlabel("Trades")
    plt.ylabel("EUR")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(CHART_EQUITY_PATH, dpi=180)
    plt.close()

    return CHART_EQUITY_PATH


def create_top_symbols_chart(top_symbols):
    if not top_symbols:
        return None

    _ensure_reports_dir()

    labels = [item["symbol"] for item in top_symbols]
    values = [item["pnl"] for item in top_symbols]

    plt.figure(figsize=(8.6, 4.8))
    plt.bar(labels, values)
    plt.title("Top-Aktien nach P/L")
    plt.xlabel("Symbol")
    plt.ylabel("P/L EUR")
    plt.grid(True, axis="y")
    plt.tight_layout()
    plt.savefig(CHART_TOP_SYMBOLS_PATH, dpi=180)
    plt.close()

    return CHART_TOP_SYMBOLS_PATH


def _performance_comment(metrics):
    comments = []

    if metrics["total_pnl"] > 0:
        comments.append("Die Simulation ist aktuell profitabel.")
    elif metrics["total_pnl"] < 0:
        comments.append("Die Simulation ist aktuell negativ.")
    else:
        comments.append("Die Simulation ist aktuell neutral.")

    if metrics["sharpe"] >= 1.5:
        comments.append("Die Sharpe Ratio wirkt stark.")
    elif metrics["sharpe"] >= 0.75:
        comments.append("Die Sharpe Ratio ist ordentlich, aber ausbaufähig.")
    else:
        comments.append("Die Sharpe Ratio ist schwach und sollte überprüft werden.")

    if metrics["max_drawdown_pct"] <= 10:
        comments.append("Der Drawdown wirkt kontrolliert.")
    elif metrics["max_drawdown_pct"] <= 20:
        comments.append("Der Drawdown ist noch vertretbar.")
    else:
        comments.append("Der Drawdown ist relativ hoch.")

    return comments


def build_pdf(metrics, equity_chart_path, top_symbols_chart_path, trades, top_symbols):
    _ensure_reports_dir()
    output_path = _build_output_path()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="PremiumTitle",
        parent=styles["Title"],
        fontSize=24,
        spaceAfter=12,
    )

    subtitle_style = ParagraphStyle(
        name="PremiumSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.grey,
        spaceAfter=6,
    )

    section_style = ParagraphStyle(
        name="PremiumSection",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        name="PremiumBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=5,
    )

    content = []

    content.append(Spacer(1, 4.2 * cm))
    content.append(Paragraph("TRADING REPORT", title_style))
    content.append(Paragraph("Premium v4 – echte Simulationsdaten", subtitle_style))
    content.append(Spacer(1, 1.0 * cm))
    content.append(
        Paragraph(
            f"Generiert am: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            body_style,
        )
    )
    content.append(
        Paragraph(
            f"Datengrundlage: {len(trades)} abgeschlossene Simulations-Trades",
            body_style,
        )
    )
    content.append(PageBreak())

    content.append(Paragraph("Executive Summary", section_style))
    for line in _performance_comment(metrics):
        content.append(Paragraph(f"• {line}", body_style))
    content.append(Spacer(1, 10))

    kpi_data = [
        ["KPI", "Wert", "Bedeutung"],
        ["Trades", str(metrics["trades"]), "Anzahl abgeschlossener Trades"],
        ["Gesamt P/L", f"{metrics['total_pnl']:.2f} EUR", "Gesamter Gewinn/Verlust"],
        ["Ø Trade", f"{metrics['avg_pnl']:.2f} EUR", "Durchschnitt pro Trade"],
        ["Trefferquote", f"{metrics['win_rate']:.2f} %", "Anteil Gewinntrades"],
        ["Sharpe", f"{metrics['sharpe']:.2f}", "Rendite relativ zur Schwankung"],
        ["Max Drawdown", f"{metrics['max_drawdown_pct']:.2f} %", "Größter Rückgang vom Hoch"],
        ["Expectancy", f"{metrics['expectancy']:.2f} EUR", "Erwartungswert pro Trade"],
        ["Best Trade", f"{metrics['best_trade']:.2f} EUR", "Bester Einzeltrade"],
        ["Worst Trade", f"{metrics['worst_trade']:.2f} EUR", "Schwächster Einzeltrade"],
        ["Endkapital", f"{metrics['final_equity']:.2f} EUR", "Startkapital 10.000 EUR + P/L"],
    ]

    kpi_table = Table(kpi_data, colWidths=[4.1 * cm, 4.1 * cm, 7.0 * cm])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    content.append(kpi_table)
    content.append(Spacer(1, 18))

    content.append(Paragraph("Equity Curve", section_style))
    if equity_chart_path and os.path.exists(equity_chart_path):
        content.append(Image(equity_chart_path, width=16 * cm, height=8.2 * cm))
    else:
        content.append(Paragraph("Keine Equity Curve verfügbar.", body_style))

    content.append(Spacer(1, 18))
    content.append(Paragraph("Top-Aktien nach Performance", section_style))

    if top_symbols_chart_path and os.path.exists(top_symbols_chart_path):
        content.append(Image(top_symbols_chart_path, width=16 * cm, height=8.2 * cm))
    else:
        content.append(Paragraph("Kein Top-Aktien-Chart verfügbar.", body_style))

    content.append(PageBreak())
    content.append(Paragraph("Top-Aktien – Detailübersicht", section_style))

    if top_symbols:
        top_table_data = [["Symbol", "Firma", "Trades", "P/L EUR", "Trefferquote", "Ø Score"]]
        for item in top_symbols:
            top_table_data.append(
                [
                    item["symbol"],
                    item["company"],
                    str(item["trades"]),
                    f"{item['pnl']:.2f}",
                    f"{item['hit_rate']:.2f} %",
                    f"{item['avg_score']:.2f}",
                ]
            )

        top_table = Table(
            top_table_data,
            colWidths=[2.1 * cm, 6.6 * cm, 1.9 * cm, 2.4 * cm, 2.7 * cm, 2.0 * cm],
        )
        top_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        content.append(top_table)
    else:
        content.append(Paragraph("Keine Top-Aktien vorhanden.", body_style))

    content.append(Spacer(1, 18))
    content.append(Paragraph("Hinweis", section_style))
    content.append(
        Paragraph(
            "Nur Simulation. Keine echten Orders. Keine Anlageberatung.",
            body_style,
        )
    )

    doc.build(content)

    _copy_to_latest(output_path)
    _cleanup_old_reports()

    print(f"PDF erstellt: {output_path}")
    print(f"Latest aktualisiert: {LATEST_PDF_PATH}")

    return output_path


def build_report_context():
    trades = load_trades()
    metrics = calculate_metrics(trades)
    equity = build_equity_curve(trades)
    top_symbols = summarize_top_symbols(trades)

    return {
        "trades": trades,
        "metrics": metrics,
        "equity": equity,
        "top_symbols": top_symbols,
    }


def run():
    context = build_report_context()
    equity_chart = create_equity_chart(context["equity"])
    top_symbols_chart = create_top_symbols_chart(context["top_symbols"])

    return build_pdf(
        metrics=context["metrics"],
        equity_chart_path=equity_chart,
        top_symbols_chart_path=top_symbols_chart,
        trades=context["trades"],
        top_symbols=context["top_symbols"],
    )


if __name__ == "__main__":
    run()
