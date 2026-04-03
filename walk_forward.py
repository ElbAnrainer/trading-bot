"""Legacy report-oriented walk-forward command.

This module is intentionally kept for compatibility with existing scripts,
checks and GitHub workflow automation that expect ``python walk_forward.py``.
Unlike ``walkforward.py`` it focuses on generating summary artifacts in
the configured reports directory and is not the walk-forward implementation
used by ``main.py``.
"""

import csv
import json
from datetime import datetime
from pathlib import Path

from analysis_engine import run_analysis
from cli import choose_interval
from config import BENCHMARK_SYMBOL, DEFAULT_MIN_VOLUME, DEFAULT_TOP_N, REPORTS_DIR as DEFAULT_REPORTS_DIR
from data_loader import fallback_rate_to_eur, latest_rate_to_eur, load_ticker_metadata
from market_data_cache import load_benchmark_cached


REPORTS_DIR = Path(DEFAULT_REPORTS_DIR)
WALK_FORWARD_DIR = REPORTS_DIR / "walk_forward"

DEFAULT_PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "3y"]


def _ensure_dirs():
    WALK_FORWARD_DIR.mkdir(parents=True, exist_ok=True)


def _company_name(symbol, cache):
    if symbol not in cache:
        try:
            meta = load_ticker_metadata(symbol)
            cache[symbol] = meta.get("name", symbol)
        except Exception:
            cache[symbol] = symbol
    return cache[symbol]


def _period_sort_key(period):
    order = {
        "1d": 1,
        "5d": 2,
        "1wk": 3,
        "1mo": 4,
        "3mo": 5,
        "6mo": 6,
        "1y": 7,
        "2y": 8,
        "3y": 9,
    }
    return order.get(period, 999)


def _benchmark_return_pct(period):
    interval = choose_interval(period)
    df = load_benchmark_cached(BENCHMARK_SYMBOL, period, interval, ttl_seconds=900)

    if df is None or df.empty or "Close" not in df.columns:
        return 0.0

    first_close = float(df.iloc[0]["Close"])
    last_close = float(df.iloc[-1]["Close"])

    if first_close == 0:
        return 0.0

    return ((last_close - first_close) / first_close) * 100.0


def _summarize_run(period, run_result):
    results = run_result.get("results", []) if run_result else []
    future_candidates = run_result.get("future_candidates", []) if run_result else []

    total_pnl = sum(float(r.get("pnl_eur", 0.0)) for r in results)
    total_trades = sum(int(r.get("trade_count", 0)) for r in results)

    wins = 0
    losses = 0
    for result in results:
        for trade in result.get("closed_trades", []):
            pnl = float(trade.get("pnl_eur", 0.0))
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1

    hit_rate = 0.0
    if (wins + losses) > 0:
        hit_rate = (wins / (wins + losses)) * 100.0

    benchmark_pct = _benchmark_return_pct(period)

    ranked_results = sorted(results, key=lambda x: float(x.get("pnl_eur", 0.0)), reverse=True)
    best_symbol = ranked_results[0]["symbol"] if ranked_results else "-"
    worst_symbol = ranked_results[-1]["symbol"] if ranked_results else "-"

    return {
        "period": period,
        "result_count": len(results),
        "candidate_count": len(future_candidates),
        "total_pnl_eur": round(total_pnl, 2),
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "hit_rate_pct": round(hit_rate, 2),
        "benchmark_return_pct": round(benchmark_pct, 2),
        "excess_return_pct": round(
            ((total_pnl / 10000.0) * 100.0) - benchmark_pct if results else -benchmark_pct,
            2,
        ),
        "best_symbol": best_symbol,
        "worst_symbol": worst_symbol,
        "results": results,
        "future_candidates": future_candidates,
    }


def _write_csv(summary, csv_path):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "period",
                "result_count",
                "candidate_count",
                "total_pnl_eur",
                "total_trades",
                "wins",
                "losses",
                "hit_rate_pct",
                "benchmark_return_pct",
                "excess_return_pct",
                "best_symbol",
                "worst_symbol",
            ]
        )

        for item in summary["windows"]:
            writer.writerow(
                [
                    item["period"],
                    item["result_count"],
                    item["candidate_count"],
                    item["total_pnl_eur"],
                    item["total_trades"],
                    item["wins"],
                    item["losses"],
                    item["hit_rate_pct"],
                    item["benchmark_return_pct"],
                    item["excess_return_pct"],
                    item["best_symbol"],
                    item["worst_symbol"],
                ]
            )


def _write_json(summary, json_path):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def _write_xml(summary, xml_path):
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append("<walk_forward_report>")
    lines.append(f"  <generated_at>{summary['generated_at']}</generated_at>")
    lines.append("  <windows>")

    for item in summary["windows"]:
        lines.append(f'    <window period="{item["period"]}">')
        lines.append(f'      <result_count>{item["result_count"]}</result_count>')
        lines.append(f'      <candidate_count>{item["candidate_count"]}</candidate_count>')
        lines.append(f'      <total_pnl_eur>{item["total_pnl_eur"]}</total_pnl_eur>')
        lines.append(f'      <total_trades>{item["total_trades"]}</total_trades>')
        lines.append(f'      <wins>{item["wins"]}</wins>')
        lines.append(f'      <losses>{item["losses"]}</losses>')
        lines.append(f'      <hit_rate_pct>{item["hit_rate_pct"]}</hit_rate_pct>')
        lines.append(f'      <benchmark_return_pct>{item["benchmark_return_pct"]}</benchmark_return_pct>')
        lines.append(f'      <excess_return_pct>{item["excess_return_pct"]}</excess_return_pct>')
        lines.append(f'      <best_symbol>{item["best_symbol"]}</best_symbol>')
        lines.append(f'      <worst_symbol>{item["worst_symbol"]}</worst_symbol>')
        lines.append("    </window>")

    lines.append("  </windows>")
    lines.append("  <summary>")
    lines.append(f'    <window_count>{summary["window_count"]}</window_count>')
    lines.append(f'    <combined_pnl_eur>{summary["combined_pnl_eur"]}</combined_pnl_eur>')
    lines.append(f'    <combined_trades>{summary["combined_trades"]}</combined_trades>')
    lines.append(f'    <combined_hit_rate_pct>{summary["combined_hit_rate_pct"]}</combined_hit_rate_pct>')
    lines.append(f'    <avg_benchmark_return_pct>{summary["avg_benchmark_return_pct"]}</avg_benchmark_return_pct>')
    lines.append(f'    <avg_excess_return_pct>{summary["avg_excess_return_pct"]}</avg_excess_return_pct>')
    lines.append("  </summary>")
    lines.append("</walk_forward_report>")

    xml_path.write_text("\n".join(lines), encoding="utf-8")


def _write_text(summary, txt_path):
    lines = []
    lines.append("WALK-FORWARD REPORT")
    lines.append("=" * 72)
    lines.append(f"Erstellt am: {summary['generated_at']}")
    lines.append("Hinweis: Nur Simulation, keine echten Orders, keine Anlageberatung.")
    lines.append("")

    lines.append("ZEITFENSTER")
    lines.append("-" * 72)

    for item in summary["windows"]:
        lines.append(
            f"{item['period']:>3} | "
            f"P/L {item['total_pnl_eur']:>9.2f} EUR | "
            f"Trades {item['total_trades']:>4} | "
            f"Treffer {item['hit_rate_pct']:>6.2f}% | "
            f"Benchmark {item['benchmark_return_pct']:>7.2f}% | "
            f"Excess {item['excess_return_pct']:>7.2f}%"
        )

    lines.append("")
    lines.append("GESAMT")
    lines.append("-" * 72)
    lines.append(f"Fenster gesamt       : {summary['window_count']}")
    lines.append(f"Kombinierter P/L     : {summary['combined_pnl_eur']:.2f} EUR")
    lines.append(f"Kombinierte Trades   : {summary['combined_trades']}")
    lines.append(f"Kombinierte Trefferq.: {summary['combined_hit_rate_pct']:.2f}%")
    lines.append(f"Ø Benchmark-Rendite  : {summary['avg_benchmark_return_pct']:.2f}%")
    lines.append(f"Ø Excess Return      : {summary['avg_excess_return_pct']:.2f}%")
    lines.append("")

    txt_path.write_text("\n".join(lines), encoding="utf-8")


def _write_html(summary, html_path):
    rows = []
    for item in summary["windows"]:
        rows.append(
            f"""
            <tr>
                <td>{item["period"]}</td>
                <td>{item["total_pnl_eur"]:.2f} EUR</td>
                <td>{item["total_trades"]}</td>
                <td>{item["hit_rate_pct"]:.2f}%</td>
                <td>{item["benchmark_return_pct"]:.2f}%</td>
                <td>{item["excess_return_pct"]:.2f}%</td>
                <td>{item["best_symbol"]}</td>
                <td>{item["worst_symbol"]}</td>
            </tr>
            """
        )

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <title>Walk-Forward Report</title>
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
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background: #f0f0f0;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Walk-Forward Report</h1>
        <p>Erstellt am: {summary["generated_at"]}</p>
        <p>Nur Simulation, keine echten Orders, keine Anlageberatung.</p>

        <h2>Übersicht</h2>
        <p>
            Fenster: {summary["window_count"]}<br>
            Kombinierter P/L: {summary["combined_pnl_eur"]:.2f} EUR<br>
            Kombinierte Trades: {summary["combined_trades"]}<br>
            Kombinierte Trefferquote: {summary["combined_hit_rate_pct"]:.2f}%<br>
            Ø Benchmark-Rendite: {summary["avg_benchmark_return_pct"]:.2f}%<br>
            Ø Excess Return: {summary["avg_excess_return_pct"]:.2f}%
        </p>

        <h2>Zeitfenster</h2>
        <table>
            <thead>
                <tr>
                    <th>Fenster</th>
                    <th>P/L</th>
                    <th>Trades</th>
                    <th>Trefferquote</th>
                    <th>Benchmark</th>
                    <th>Excess Return</th>
                    <th>Bestes Symbol</th>
                    <th>Schwächstes Symbol</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")


def _write_pdf(summary, pdf_path):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ImportError:
        print("PDF-Erzeugung übersprungen: reportlab ist nicht installiert.")
        return False

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)

    elements = []
    elements.append(Paragraph("Walk-Forward Report", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Erstellt am: {summary['generated_at']}", styles["BodyText"]))
    elements.append(Paragraph("Nur Simulation, keine echten Orders, keine Anlageberatung.", styles["BodyText"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Gesamtübersicht", styles["Heading2"]))
    elements.append(Paragraph(f"Fenster gesamt: {summary['window_count']}", styles["BodyText"]))
    elements.append(Paragraph(f"Kombinierter P/L: {summary['combined_pnl_eur']:.2f} EUR", styles["BodyText"]))
    elements.append(Paragraph(f"Kombinierte Trades: {summary['combined_trades']}", styles["BodyText"]))
    elements.append(Paragraph(f"Kombinierte Trefferquote: {summary['combined_hit_rate_pct']:.2f}%", styles["BodyText"]))
    elements.append(Paragraph(f"Ø Benchmark-Rendite: {summary['avg_benchmark_return_pct']:.2f}%", styles["BodyText"]))
    elements.append(Paragraph(f"Ø Excess Return: {summary['avg_excess_return_pct']:.2f}%", styles["BodyText"]))
    elements.append(Spacer(1, 12))

    data = [[
        "Fenster",
        "P/L EUR",
        "Trades",
        "Trefferquote",
        "Benchmark %",
        "Excess %",
        "Bestes",
        "Schwächstes",
    ]]

    for item in summary["windows"]:
        data.append([
            item["period"],
            f"{item['total_pnl_eur']:.2f}",
            str(item["total_trades"]),
            f"{item['hit_rate_pct']:.2f}",
            f"{item['benchmark_return_pct']:.2f}",
            f"{item['excess_return_pct']:.2f}",
            item["best_symbol"],
            item["worst_symbol"],
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    elements.append(Paragraph("Zeitfenster", styles["Heading2"]))
    elements.append(table)

    doc.build(elements)
    return True


def run_walk_forward(
    periods=None,
    top_n=DEFAULT_TOP_N,
    min_volume=DEFAULT_MIN_VOLUME,
    long_mode=False,
):
    _ensure_dirs()

    if periods is None:
        periods = list(DEFAULT_PERIODS)

    periods = sorted(periods, key=_period_sort_key)

    windows = []

    for period in periods:
        print(f"\n>>> Starte Walk-Forward-Fenster {period}")
        result = run_analysis(
            period=period,
            top_n=top_n,
            min_volume=min_volume,
            long_mode=long_mode,
        )
        windows.append(_summarize_run(period, result))

    combined_pnl = sum(item["total_pnl_eur"] for item in windows)
    combined_trades = sum(item["total_trades"] for item in windows)
    combined_wins = sum(item["wins"] for item in windows)
    combined_losses = sum(item["losses"] for item in windows)

    combined_hit_rate = 0.0
    if (combined_wins + combined_losses) > 0:
        combined_hit_rate = (combined_wins / (combined_wins + combined_losses)) * 100.0

    avg_benchmark = 0.0
    avg_excess = 0.0
    if windows:
        avg_benchmark = sum(item["benchmark_return_pct"] for item in windows) / len(windows)
        avg_excess = sum(item["excess_return_pct"] for item in windows) / len(windows)

    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "window_count": len(windows),
        "combined_pnl_eur": round(combined_pnl, 2),
        "combined_trades": combined_trades,
        "combined_hit_rate_pct": round(combined_hit_rate, 2),
        "avg_benchmark_return_pct": round(avg_benchmark, 2),
        "avg_excess_return_pct": round(avg_excess, 2),
        "windows": windows,
    }

    timestamp = datetime.now().strftime("%Y-%m-%d")
    txt_path = WALK_FORWARD_DIR / f"walk_forward_{timestamp}.txt"
    html_path = WALK_FORWARD_DIR / f"walk_forward_{timestamp}.html"
    csv_path = WALK_FORWARD_DIR / f"walk_forward_{timestamp}.csv"
    json_path = WALK_FORWARD_DIR / f"walk_forward_{timestamp}.json"
    xml_path = WALK_FORWARD_DIR / f"walk_forward_{timestamp}.xml"
    pdf_path = WALK_FORWARD_DIR / f"walk_forward_{timestamp}.pdf"

    latest_txt = REPORTS_DIR / "walk_forward_latest.txt"
    latest_html = REPORTS_DIR / "walk_forward_latest.html"
    latest_csv = REPORTS_DIR / "walk_forward_latest.csv"
    latest_json = REPORTS_DIR / "walk_forward_latest.json"
    latest_xml = REPORTS_DIR / "walk_forward_latest.xml"
    latest_pdf = REPORTS_DIR / "walk_forward_latest.pdf"

    _write_text(summary, txt_path)
    _write_html(summary, html_path)
    _write_csv(summary, csv_path)
    _write_json(summary, json_path)
    _write_xml(summary, xml_path)

    _write_text(summary, latest_txt)
    _write_html(summary, latest_html)
    _write_csv(summary, latest_csv)
    _write_json(summary, latest_json)
    _write_xml(summary, latest_xml)

    pdf_created = _write_pdf(summary, pdf_path)
    if pdf_created:
        _write_pdf(summary, latest_pdf)

    print("\nWalk-Forward abgeschlossen.")
    print(f"TXT  : {txt_path}")
    print(f"HTML : {html_path}")
    print(f"CSV  : {csv_path}")
    print(f"JSON : {json_path}")
    print(f"XML  : {xml_path}")
    if pdf_created:
        print(f"PDF  : {pdf_path}")

    return summary


if __name__ == "__main__":
    run_walk_forward()
