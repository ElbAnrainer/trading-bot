import json
from pathlib import Path

from report_writer import save_run_outputs


def test_save_run_outputs_creates_files(tmp_path):
    results = [
        {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "isin": "US0378331005",
            "wkn": "865985",
            "signal": "BUY",
            "native_currency": "USD",
            "pnl_eur": 123.45,
            "pnl_native": 134.56,
            "pnl_pct_eur": 1.23,
            "trade_count": 4,
            "last_price_eur": 200.0,
            "last_price_native": 217.0,
            "initial_cash_eur": 10000.0,
            "current_equity_eur": 10123.45,
        }
    ]
    portfolio = {
        "AAPL": {
            "qty": 10,
            "price_eur": 200.0,
            "price_native": 217.0,
            "native_currency": "USD",
            "isin": "US0378331005",
            "wkn": "865985",
        }
    }

    save_run_outputs(
        output_dir=tmp_path,
        period="1mo",
        interval="5m",
        results=results,
        portfolio=portfolio,
    )

    latest_json = Path(tmp_path) / "latest_run.json"
    history_csv = Path(tmp_path) / "history.csv"
    dashboard_html = Path(tmp_path) / "dashboard.html"

    assert latest_json.exists()
    assert history_csv.exists()
    assert dashboard_html.exists()

    data = json.loads(latest_json.read_text(encoding="utf-8"))
    assert data["period"] == "1mo"
    assert len(data["results"]) == 1
    assert data["results"][0]["symbol"] == "AAPL"
    html = dashboard_html.read_text(encoding="utf-8")
    assert "US0378331005" in html
    assert "865985" in html
