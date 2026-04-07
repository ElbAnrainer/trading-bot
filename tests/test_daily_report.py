import csv
import xml.etree.ElementTree as ET

import daily_report


def _pipe_positions(text):
    return [idx for idx, char in enumerate(text) if char == "|"]


def _sample_dashboard_data():
    return {
        "analysis": {
            "source": "current_run",
            "generated_at": "2026-04-03T20:15:00Z",
            "period": "1mo",
            "interval": "5m",
            "current_results": [
                {
                    "symbol": "NVDA",
                    "company": "NVIDIA Corporation",
                    "isin": "US67066G1040",
                    "wkn": "918422",
                    "signal": "BUY",
                    "pnl_eur": 321.0,
                    "trade_count": 7,
                    "score": 72.5,
                    "explanation_summary": "Kaufsignal wegen Breakout und Momentum.",
                    "explanation_points": ["These: Breakout | Momentum"],
                }
            ],
            "future_candidates": [
                {
                    "symbol": "MSFT",
                    "company": "Microsoft Corporation",
                    "isin": "US5949181045",
                    "wkn": "870747",
                    "future_signal": "WATCH",
                    "score": 61.25,
                    "learned_bonus": 12.0,
                    "explanation_summary": "Beobachtungskandidat mit sauberem Trendbild.",
                    "explanation_points": ["Qualität: Score 61.25 | Risiko mittel"],
                }
            ],
            "trading_plan": [
                {
                    "symbol": "MSFT",
                    "company": "Microsoft Corporation",
                    "isin": "US5949181045",
                    "wkn": "870747",
                    "weight": 0.25,
                    "capital": 250.0,
                    "learned_score": 44.0,
                    "explanation_summary": "Im Trading-Plan mit 25.0% Gewicht.",
                    "explanation_points": ["Allokation: 25.0% = 250.00 EUR"],
                }
            ],
            "simulated_portfolio": [
                {
                    "symbol": "NVDA",
                    "company": "NVIDIA Corporation",
                    "isin": "US67066G1040",
                    "wkn": "918422",
                    "qty": 2.0,
                    "price_eur": 150.0,
                    "value_eur": 300.0,
                }
            ],
            "orders": [
                {
                    "action": "BUY",
                    "symbol": "MSFT",
                    "reason": "WATCH_TOP_SELECTION",
                    "reason_label": "Top-Auswahl trotz Watch-Signal",
                    "capital": 250.0,
                    "weight": 0.25,
                    "learned_score": 44.0,
                    "explanation_summary": "Kaufauftrag trotz Watch-Signal.",
                    "explanation_points": ["Auslöser: Top-Auswahl trotz Watch-Signal"],
                }
            ],
        },
        "performance": {
            "total_entries": 10,
            "buy_signals": 4,
            "sell_signals": 2,
            "watch_signals": 3,
            "hold_signals": 1,
            "stocks_total": 5,
            "closed_trades": 6,
            "winning_trades": 4,
            "losing_trades": 2,
            "hit_rate": 66.67,
            "realized_pnl": 123.45,
            "avg_trade_pnl": 20.58,
            "top_symbols": [
                {
                    "symbol": "AAPL",
                    "company": "Apple Inc.",
                    "isin": "US0378331005",
                    "wkn": "865985",
                    "count": 9,
                },
                {
                    "symbol": "SAP",
                    "company": "SAP SE",
                    "isin": "DE0007164600",
                    "wkn": "716460",
                    "count": 3,
                },
            ],
            "ranking": [],
        },
        "profile": {"name": "konservativ"},
        "state": {
            "cash_eur": 500.0,
            "total_invested_eur": 300.0,
            "last_equity_eur": 820.0,
            "peak_equity_eur": 900.0,
            "drawdown_pct": 8.89,
            "positions": 2,
            "updated_at": "2026-04-03T20:16:00Z",
        },
        "risk": {
            "max_position_pct": 0.25,
            "stop_loss_pct": 0.08,
            "trailing_stop_pct": 0.12,
            "max_drawdown_pct": 0.15,
        },
    }


def _build_sample_report(monkeypatch):
    monkeypatch.setattr(daily_report, "build_dashboard_data", lambda: _sample_dashboard_data())
    return daily_report._build_report_data()


def test_build_report_data_uses_dashboard_sections(monkeypatch):
    report = _build_sample_report(monkeypatch)

    assert report["analysis_source"] == "current_run"
    assert report["analysis_source_label"] == "Aktueller CLI-Lauf"
    assert report["analysis_result_count"] == 1
    assert report["analysis_candidate_count"] == 1
    assert report["analysis_order_count"] == 1
    assert report["profile_name"] == "konservativ"
    assert report["buy_signals"] == 4
    assert report["stocks_total"] == 5
    assert report["trading_plan"][0]["symbol"] == "MSFT"
    assert report["orders"][0]["action"] == "BUY"
    assert report["simulated_portfolio"][0]["symbol"] == "NVDA"
    assert report["state_cash_eur"] == 500.0
    assert report["risk_stop_loss_pct"] == 8.0
    assert report["top_symbols"][0]["isin"] == "US0378331005"


def test_build_text_report_includes_current_sections_and_aligns_top_stock_columns(monkeypatch):
    report = _build_sample_report(monkeypatch)

    text = daily_report._build_text_report(report)
    lines = text.splitlines()

    header = next(line for line in lines if "SYM" in line and "ANZAHL" in line)
    rows = [line for line in lines if line.startswith("AAPL") or line.startswith("SAP")]
    expected = _pipe_positions(header)

    assert "AKTUELLER TRADING-PLAN" in text
    assert "AKTUELLE ORDERS" in text
    assert "SIMULIERTES DEPOT (AKTUELLER LAUF)" in text
    assert "WARUM DIESER TRADING-PLAN" in text
    assert "Top-Auswahl trotz Watch-Signal" in text
    assert "US5949181045" in text
    assert "US0378331005" in text
    assert expected
    assert rows
    assert all(_pipe_positions(line) == expected for line in rows)


def test_build_html_report_includes_analysis_state_and_orders_sections(monkeypatch):
    report = _build_sample_report(monkeypatch)

    html = daily_report._build_html_report(report)

    assert "Aktueller Analyse-Lauf" in html
    assert "Aktueller Trading-Plan" in html
    assert "Aktuelle Orders" in html
    assert "Simuliertes Depot (aktueller Lauf)" in html
    assert "Mini-System / Depot-State" in html
    assert "Im Trading-Plan mit 25.0% Gewicht." in html
    assert "US67066G1040" in html
    assert "918422" in html


def test_write_csv_and_xml_include_analysis_and_nested_sections(monkeypatch, tmp_path):
    report = _build_sample_report(monkeypatch)
    csv_path = tmp_path / "daily_report.csv"
    xml_path = tmp_path / "daily_report.xml"

    monkeypatch.setattr(daily_report, "CSV_PATH", str(csv_path))
    monkeypatch.setattr(daily_report, "XML_PATH", str(xml_path))

    daily_report._write_csv(report)
    daily_report._write_xml(report)

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = dict(csv.reader(f))

    assert rows["analysis_source_label"] == "Aktueller CLI-Lauf"
    assert rows["state_cash_eur"] == "500.0"
    assert rows["orders_rows"] == "1"

    tree = ET.parse(xml_path)
    root = tree.getroot()

    assert root.findtext("analysis_source") == "current_run"
    assert root.find("current_results/row/symbol").text == "NVDA"
    assert root.find("future_candidates/row/isin").text == "US5949181045"
    assert root.find("trading_plan/row/symbol").text == "MSFT"
    assert root.find("orders/row/action").text == "BUY"
    assert root.find("orders/row/reason_label").text == "Top-Auswahl trotz Watch-Signal"
    assert root.find("simulated_portfolio/row/wkn").text == "918422"


def test_create_daily_report_writes_all_outputs(monkeypatch, tmp_path):
    monkeypatch.setattr(daily_report, "build_dashboard_data", lambda: _sample_dashboard_data())
    monkeypatch.setattr(daily_report, "TXT_PATH", str(tmp_path / "daily_report.txt"))
    monkeypatch.setattr(daily_report, "HTML_PATH", str(tmp_path / "daily_report.html"))
    monkeypatch.setattr(daily_report, "CSV_PATH", str(tmp_path / "daily_report.csv"))
    monkeypatch.setattr(daily_report, "XML_PATH", str(tmp_path / "daily_report.xml"))
    monkeypatch.setattr(daily_report, "PDF_PATH", str(tmp_path / "daily_report.pdf"))
    monkeypatch.setattr(daily_report, "ensure_reports_dir", lambda: str(tmp_path))

    report = daily_report.create_daily_report()

    assert report["analysis_source"] == "current_run"
    assert (tmp_path / "daily_report.txt").exists()
    assert (tmp_path / "daily_report.html").exists()
    assert (tmp_path / "daily_report.csv").exists()
    assert (tmp_path / "daily_report.xml").exists()
    assert (tmp_path / "daily_report.pdf").exists()
    assert (tmp_path / "daily_report.pdf").stat().st_size > 0
