from __future__ import annotations

import csv
import json
import os
import shutil
from datetime import datetime
from statistics import mean, pstdev
from typing import Any

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import (
    CHART_PATH as DEFAULT_CHART_PATH,
    LEGACY_REALISTIC_BACKTEST_JSON,
    LEGACY_TRADING_JOURNAL_CSV,
    REALISTIC_BACKTEST_JSON as DEFAULT_REALISTIC_BACKTEST_JSON,
    REPORTS_DIR as DEFAULT_REPORTS_DIR,
    ROOT_TRADING_JOURNAL_CSV,
    TRADING_JOURNAL_CSV,
    TRADING_REPORT_PDF as DEFAULT_LATEST_PDF_PATH,
    ensure_reports_dir,
    get_active_profile_name,
    get_trading_config,
)


REPORTS_DIR = DEFAULT_REPORTS_DIR
JOURNAL_CANDIDATES = [
    TRADING_JOURNAL_CSV,
    LEGACY_TRADING_JOURNAL_CSV,
    ROOT_TRADING_JOURNAL_CSV,
]
REALISTIC_BACKTEST_JSON = DEFAULT_REALISTIC_BACKTEST_JSON

CHART_PATH = DEFAULT_CHART_PATH
REALISTIC_CHART_PATH = os.path.join(REPORTS_DIR, "equity_curve_realistic.png")
LATEST_PDF_PATH = DEFAULT_LATEST_PDF_PATH


def _ensure_reports_dir() -> None:
    ensure_reports_dir()


def _build_output_path() -> str:
    _ensure_reports_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join(REPORTS_DIR, f"trading_report_{timestamp}.pdf")


def _find_journal_path() -> str:
    for path in JOURNAL_CANDIDATES:
        if os.path.exists(path):
            return path
    return JOURNAL_CANDIDATES[0]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def load_trades() -> list[dict[str, Any]]:
    report_path = _find_journal_path()
    if not os.path.exists(report_path):
        return []

    trades: list[dict[str, Any]] = []
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
                    "isin": row.get("isin", "-").strip(),
                    "wkn": row.get("wkn", "-").strip(),
                    "score": _to_float(row.get("score", 0.0), 0.0),
                    "pnl_eur": pnl,
                    "time": row.get("timestamp") or row.get("time") or "",
                }
            )
    return trades


def load_realistic_backtest() -> dict[str, Any] | None:
    for path in (REALISTIC_BACKTEST_JSON, LEGACY_REALISTIC_BACKTEST_JSON):
        if not os.path.exists(path):
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            continue

    return None


def calculate_metrics(trades: list[dict[str, Any]], initial_capital: float = 10_000.0) -> dict[str, Any]:
    if not trades:
        return {
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "avg_pnl": 0.0,
            "trades": 0,
            "sharpe": 0.0,
            "max_drawdown_pct": 0.0,
            "expectancy": 0.0,
            "final_equity": initial_capital,
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
        "sharpe": sharpe,
        "max_drawdown_pct": max_drawdown_pct,
        "expectancy": expectancy,
        "final_equity": equity_curve[-1] if equity_curve else initial_capital,
    }


def build_equity_curve(trades: list[dict[str, Any]], initial_capital: float = 10_000.0) -> list[float]:
    equity: list[float] = []
    value = initial_capital

    for trade in trades:
        value += trade["pnl_eur"]
        equity.append(value)

    return equity


def calculate_max_drawdown_pct(equity_curve: list[float]) -> float:
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


def summarize_top_symbols(trades: list[dict[str, Any]], top_n: int = 5) -> list[dict[str, Any]]:
    by_symbol: dict[str, dict[str, Any]] = {}

    for trade in trades:
        symbol = trade["symbol"] or "-"
        if symbol not in by_symbol:
            by_symbol[symbol] = {
                "company": trade["company"] or symbol,
                "isin": trade.get("isin", "-"),
                "wkn": trade.get("wkn", "-"),
                "trades": 0,
                "pnl": 0.0,
                "scores": [],
            }

        by_symbol[symbol]["trades"] += 1
        by_symbol[symbol]["pnl"] += trade["pnl_eur"]
        if trade["score"]:
            by_symbol[symbol]["scores"].append(trade["score"])

    ranked = sorted(by_symbol.items(), key=lambda x: x[1]["pnl"], reverse=True)

    rows: list[dict[str, Any]] = []
    for symbol, data in ranked[:top_n]:
        avg_score = mean(data["scores"]) if data["scores"] else 0.0
        rows.append(
            {
                "symbol": symbol,
                "company": data["company"],
                "isin": data.get("isin", "-"),
                "wkn": data.get("wkn", "-"),
                "trades": data["trades"],
                "pnl": data["pnl"],
                "avg_score": avg_score,
            }
        )
    return rows


def create_chart(equity: list[float], output_path: str, title: str = "Equity Curve") -> str | None:
    if not equity:
        return None

    _ensure_reports_dir()

    plt.figure(figsize=(8, 4.5))
    plt.plot(equity, linewidth=2)
    plt.title(title)
    plt.xlabel("Trades")
    plt.ylabel("EUR")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()

    return output_path


def create_realistic_chart(realistic_data: dict[str, Any] | None) -> str | None:
    if not realistic_data:
        return None

    curve = realistic_data.get("equity_curve", [])
    if not curve:
        return None

    equity = [float(point.get("equity_eur", 0.0)) for point in curve]
    if not equity:
        return None

    return create_chart(
        equity,
        REALISTIC_CHART_PATH,
        title="Realistische Equity Curve (10.000 EUR)",
    )


def build_report_context() -> dict[str, Any]:
    """
    Kompatibilitätsfunktion für gmail_api_report.py.
    """
    trades = load_trades()
    realistic_data = load_realistic_backtest()
    metrics = calculate_metrics(trades)
    top_symbols = summarize_top_symbols(trades)

    profile_name = get_active_profile_name()
    profile_config = get_trading_config(profile_name)

    context: dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "profile_name": profile_name,
        "profile_config": profile_config,
        "metrics": metrics,
        "trades": trades,
        "top_symbols": top_symbols,
        "realistic_backtest": realistic_data,
        "reports_dir": REPORTS_DIR,
        "latest_pdf_path": LATEST_PDF_PATH,
        "total_pnl": metrics.get("total_pnl", 0.0),
        "win_rate": metrics.get("win_rate", 0.0),
        "avg_pnl": metrics.get("avg_pnl", 0.0),
        "trades_count": metrics.get("trades", 0),
        "final_equity": metrics.get("final_equity", 0.0),
    }

    if realistic_data:
        context["realistic_final_equity"] = realistic_data.get("final_equity", 0.0)
        context["realistic_total_return_pct"] = realistic_data.get("total_return_pct", 0.0)
        context["realistic_trade_count"] = realistic_data.get("trade_count", 0)
        context["realistic_win_rate_pct"] = realistic_data.get("win_rate_pct", 0.0)

    return context


def _build_title_page(content: list[Any], title_style: ParagraphStyle, body_style: ParagraphStyle) -> None:
    active_profile = get_active_profile_name()

    content.append(Spacer(1, 4.0 * cm))
    content.append(Paragraph("TRADING REPORT", title_style))
    content.append(Paragraph("Premium v5", body_style))
    content.append(Spacer(1, 1.2 * cm))
    content.append(
        Paragraph(
            f"Generiert am: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            body_style,
        )
    )
    content.append(Spacer(1, 0.4 * cm))
    content.append(Paragraph(f"Aktives Profil: {active_profile}", body_style))
    content.append(Spacer(1, 0.6 * cm))
    content.append(
        Paragraph(
            "Nur Simulation. Keine echten Orders. Keine Anlageberatung.",
            body_style,
        )
    )
    content.append(PageBreak())


def _build_profile_section(content: list[Any], section_style: ParagraphStyle, body_style: ParagraphStyle) -> None:
    active_profile = get_active_profile_name()
    cfg = get_trading_config(active_profile)

    content.append(Paragraph("Aktives Profil", section_style))

    table_data = [
        ["Parameter", "Wert"],
        ["Profilname", active_profile],
        ["Initiales Kapital", f"{float(cfg.get('initial_capital', 0.0)):.2f} EUR"],
        ["Max Positionen", str(cfg.get("max_positions", "-"))],
        ["Stop-Loss", f"{float(cfg.get('stop_loss_pct', 0.0)):.2%}"],
        ["Trailing Stop", f"{float(cfg.get('trailing_stop_pct', 0.0)):.2%}"],
        ["Mindesthaltedauer", str(cfg.get("min_hold_bars", "-"))],
        ["Cooldown", str(cfg.get("cooldown_bars", "-"))],
        ["Max Trades/Woche", str(cfg.get("max_new_trades_per_week", "-"))],
        ["Min Learned Score", f"{float(cfg.get('min_learned_score', 0.0)):.2f}"],
        ["Max Volatilität 20", f"{float(cfg.get('max_volatility_20', 0.0)):.4f}"],
        ["Min erwarteter Edge", f"{float(cfg.get('min_expected_edge_pct', 0.0)):.2%}"],
    ]

    table = Table(table_data, colWidths=[6 * cm, 6 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    content.append(table)
    content.append(Spacer(1, 16))
    content.append(
        Paragraph(
            "Alle Backtest- und Trading-Ergebnisse in diesem Bericht basieren auf diesem aktiven Profil.",
            body_style,
        )
    )
    content.append(PageBreak())


def _build_signal_section(
    content: list[Any],
    metrics: dict[str, Any],
    chart_path: str | None,
    top_symbols: list[dict[str, Any]],
    section_style: ParagraphStyle,
    body_style: ParagraphStyle,
) -> None:
    content.append(Paragraph("Signal- und Journal-Auswertung", section_style))

    table_data = [
        ["Metrik", "Wert"],
        ["Trades", str(metrics["trades"])],
        ["Gesamt P/L", f"{metrics['total_pnl']:.2f} EUR"],
        ["Ø Trade", f"{metrics['avg_pnl']:.2f} EUR"],
        ["Trefferquote", f"{metrics['win_rate']:.2f}%"],
        ["Sharpe", f"{metrics['sharpe']:.2f}"],
        ["Max Drawdown", f"{metrics['max_drawdown_pct']:.2f}%"],
        ["Endkapital", f"{metrics['final_equity']:.2f} EUR"],
    ]

    table = Table(table_data, colWidths=[6 * cm, 6 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    content.append(table)
    content.append(Spacer(1, 16))

    if chart_path:
        content.append(Paragraph("Signalbasierte Equity Curve", section_style))
        content.append(Image(chart_path, width=14 * cm, height=6 * cm))
        content.append(Spacer(1, 16))

    content.append(Paragraph("Top-Aktien nach Journal P/L", section_style))
    if top_symbols:
        top_table = [["Symbol", "ISIN", "WKN", "Firma", "Trades", "P/L", "Ø Score"]]
        for item in top_symbols:
            top_table.append([
                item["symbol"],
                item.get("isin", "-"),
                item.get("wkn", "-"),
                item["company"],
                str(item["trades"]),
                f"{item['pnl']:.2f} EUR",
                f"{item['avg_score']:.2f}",
            ])

        top_tbl = Table(top_table, colWidths=[1.8 * cm, 3.1 * cm, 2.0 * cm, 4.4 * cm, 1.6 * cm, 2.2 * cm, 1.8 * cm])
        top_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        content.append(top_tbl)
    else:
        content.append(Paragraph("Keine Journal-Daten vorhanden.", body_style))


def _build_realistic_section(
    content: list[Any],
    realistic_data: dict[str, Any] | None,
    realistic_chart: str | None,
    section_style: ParagraphStyle,
    body_style: ParagraphStyle,
) -> None:
    content.append(Paragraph("Realistische 10.000-EUR-Schätzung", section_style))

    if not realistic_data:
        content.append(
            Paragraph(
                "Es liegt noch kein realistischer Backtest vor. Führe zuerst einen normalen Lauf mit main.py aus.",
                body_style,
            )
        )
        return

    note = realistic_data.get("note")
    if note:
        content.append(Paragraph(f"Hinweis: {note}", body_style))
        content.append(Spacer(1, 8))

    table_data = [
        ["Metrik", "Wert"],
        ["Profil", str(realistic_data.get("profile_name", get_active_profile_name()))],
        ["Zeitraum", str(realistic_data.get("period", "-"))],
        ["Intervall", str(realistic_data.get("interval", "-"))],
        ["Startkapital", f"{float(realistic_data.get('initial_capital', 0.0)):.2f} EUR"],
        ["Endkapital", f"{float(realistic_data.get('final_equity', 0.0)):.2f} EUR"],
        ["Gesamtrendite", f"{float(realistic_data.get('total_return_pct', 0.0)):.2f}%"],
        ["CAGR", f"{float(realistic_data.get('cagr_pct', 0.0)):.2f}%"],
        ["Max Drawdown", f"{float(realistic_data.get('max_drawdown_pct', 0.0)):.2f}%"],
        ["Trades", str(int(realistic_data.get("trade_count", 0)))],
        ["Trefferquote", f"{float(realistic_data.get('win_rate_pct', 0.0)):.2f}%"],
        ["Gebühren", f"{float(realistic_data.get('fees_paid_eur', 0.0)):.2f} EUR"],
        ["Slippage", f"{float(realistic_data.get('slippage_paid_eur', 0.0)):.2f} EUR"],
    ]

    table = Table(table_data, colWidths=[6 * cm, 6 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    content.append(table)
    content.append(Spacer(1, 16))

    anti = realistic_data.get("anti_overtrading", {})
    if anti:
        content.append(Paragraph("Verwendete Regelparameter", section_style))
        anti_table = [
            ["Parameter", "Wert"],
            ["Mindesthaltedauer", str(anti.get("min_hold_bars", "-"))],
            ["Cooldown", str(anti.get("cooldown_bars", "-"))],
            ["Max neue Trades/Tag", str(anti.get("max_new_trades_per_bar", "-"))],
            ["Max Trades/Woche", str(anti.get("max_new_trades_per_week", "-"))],
            ["Min Learned Score", f"{float(anti.get('min_learned_score', 0.0)):.2f}"],
            ["Max Volatilität 20", f"{float(anti.get('max_volatility_20', 0.0)):.4f}"],
            ["Min Stop-Abstand", f"{float(anti.get('min_stop_distance_pct', 0.0)):.2%}"],
            ["Min erwarteter Edge", f"{float(anti.get('min_expected_edge_pct', 0.0)):.2%}"],
        ]
        anti_tbl = Table(anti_table, colWidths=[6 * cm, 6 * cm])
        anti_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        content.append(anti_tbl)
        content.append(Spacer(1, 16))

    symbols = realistic_data.get("symbols", [])
    if symbols:
        content.append(Paragraph("Verwendete Symbole: " + ", ".join(symbols), body_style))
        content.append(Spacer(1, 12))

    if realistic_chart:
        content.append(Paragraph("Realistische Equity Curve", section_style))
        content.append(Image(realistic_chart, width=14 * cm, height=6 * cm))
        content.append(Spacer(1, 12))

    trades = realistic_data.get("trades", [])
    content.append(Paragraph("Letzte realistische Trades", section_style))
    if trades:
        trade_table = [["Symbol", "Entry", "Exit", "P/L", "Grund"]]
        for item in trades[-10:]:
            trade_table.append([
                item.get("symbol", "-"),
                str(item.get("entry_date", "-"))[:10],
                str(item.get("exit_date", "-"))[:10],
                f"{float(item.get('pnl_eur', 0.0)):.2f} EUR",
                item.get("reason", "-"),
            ])

        tbl = Table(trade_table, colWidths=[2.0 * cm, 2.6 * cm, 2.6 * cm, 3.2 * cm, 4.8 * cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        content.append(tbl)
    else:
        content.append(Paragraph("Keine realistischen Trades vorhanden.", body_style))

    content.append(Spacer(1, 16))
    content.append(
        Paragraph(
            "Diese Sektion ist die relevante Abschätzung der Frage: "
            "Was hätte man mit 10.000 EUR ungefähr machen können?",
            body_style,
        )
    )


def build_pdf(
    metrics: dict[str, Any],
    chart_path: str | None,
    top_symbols: list[dict[str, Any]],
    realistic_data: dict[str, Any] | None,
    realistic_chart: str | None,
) -> str:
    output_path = _build_output_path()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="PremiumTitle",
        parent=styles["Title"],
        fontSize=22,
        spaceAfter=14,
    )

    section_style = ParagraphStyle(
        name="PremiumSection",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=10,
    )

    body_style = styles["Normal"]

    content: list[Any] = []

    _build_title_page(content, title_style, body_style)
    _build_profile_section(content, section_style, body_style)
    _build_realistic_section(content, realistic_data, realistic_chart, section_style, body_style)
    content.append(PageBreak())
    _build_signal_section(content, metrics, chart_path, top_symbols, section_style, body_style)

    doc.build(content)

    shutil.copyfile(output_path, LATEST_PDF_PATH)

    print(f"PDF erstellt: {output_path}")
    print(f"Latest aktualisiert: {LATEST_PDF_PATH}")

    return output_path


def run() -> str:
    trades = load_trades()
    metrics = calculate_metrics(trades)
    equity = build_equity_curve(trades)
    chart = create_chart(equity, CHART_PATH, title="Signalbasierte Equity Curve")
    top_symbols = summarize_top_symbols(trades)

    realistic_data = load_realistic_backtest()
    realistic_chart = create_realistic_chart(realistic_data)

    return build_pdf(metrics, chart, top_symbols, realistic_data, realistic_chart)


if __name__ == "__main__":
    run()
