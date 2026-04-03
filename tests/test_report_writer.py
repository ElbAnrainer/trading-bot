import json
from pathlib import Path

from report_writer import save_run_outputs, update_latest_json_context


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
        future_candidates=[
            {
                "symbol": "MSFT",
                "company_name": "Microsoft Corporation",
                "isin": "US5949181045",
                "wkn": "870747",
                "future_signal": "WATCH",
                "score": 55.0,
            }
        ],
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
    assert data["future_candidates"][0]["symbol"] == "MSFT"
    html = dashboard_html.read_text(encoding="utf-8")
    assert "US0378331005" in html
    assert "865985" in html


def test_update_latest_json_context_adds_plan_and_decisions(tmp_path):
    save_run_outputs(
        output_dir=tmp_path,
        period="1mo",
        interval="5m",
        results=[],
        portfolio={},
    )

    update_latest_json_context(
        tmp_path,
        trading_plan=[
            {
                "symbol": "NVDA",
                "company": "NVIDIA Corporation",
                "isin": "US67066G1040",
                "wkn": "918422",
                "weight": 0.2,
                "capital": 200.0,
                "learned_score": 77.0,
            }
        ],
        decisions={
            "orders": [
                {
                    "action": "BUY",
                    "symbol": "NVDA",
                    "reason": "WATCH_TOP_SELECTION",
                    "capital": 200.0,
                    "learned_score": 77.0,
                }
            ]
        },
    )

    data = json.loads((tmp_path / "latest_run.json").read_text(encoding="utf-8"))
    assert data["trading_plan"][0]["symbol"] == "NVDA"
    assert data["decisions"]["orders"][0]["action"] == "BUY"
