import json

import dashboard


def _sample_analysis_result():
    return {
        "period": "1mo",
        "interval": "5m",
        "results": [
            {
                "symbol": "NVDA",
                "company_name": "NVIDIA Corporation",
                "isin": "US67066G1040",
                "wkn": "918422",
                "signal": "BUY",
                "pnl_eur": 321.0,
                "trade_count": 7,
                "score": 72.5,
                "native_currency": "USD",
            }
        ],
        "portfolio": {
            "NVDA": {
                "qty": 10,
                "price_eur": 150.0,
                "price_native": 170.0,
                "native_currency": "USD",
                "company_name": "NVIDIA Corporation",
                "isin": "US67066G1040",
                "wkn": "918422",
            }
        },
        "future_candidates": [
            {
                "symbol": "MSFT",
                "company_name": "Microsoft Corporation",
                "isin": "US5949181045",
                "wkn": "870747",
                "future_signal": "WATCH",
                "score": 61.25,
                "learned_bonus": 12.0,
            }
        ],
    }


def _patch_dashboard_dependencies(monkeypatch):
    monkeypatch.setattr(
        dashboard,
        "analyze_performance",
        lambda: {
            "closed_trades": 3,
            "winning_trades": 2,
            "losing_trades": 1,
            "hit_rate": 66.6,
            "realized_pnl": 100.0,
            "avg_trade_pnl": 33.3,
            "ranking": [],
            "portfolio": [],
        },
    )
    monkeypatch.setattr(
        dashboard,
        "load_portfolio_state",
        lambda initial_cash=1000.0: {"positions": {}, "history": [], "last_equity_eur": initial_cash},
    )
    monkeypatch.setattr(
        dashboard,
        "portfolio_summary",
        lambda state: {
            "cash_eur": 1000.0,
            "positions": 0,
            "total_invested_eur": 0.0,
        },
    )
    monkeypatch.setattr(dashboard, "risk_summary", lambda: {})
    monkeypatch.setattr(dashboard, "get_active_profile_name", lambda: "konservativ")
    monkeypatch.setattr(dashboard, "get_trading_config", lambda profile_name: {"max_positions": 4})


def test_build_dashboard_data_prefers_current_analysis(monkeypatch):
    _patch_dashboard_dependencies(monkeypatch)

    data = dashboard.build_dashboard_data(
        analysis_result=_sample_analysis_result(),
        trading_plan=[
            {
                "symbol": "MSFT",
                "company": "Microsoft Corporation",
                "isin": "US5949181045",
                "wkn": "870747",
                "weight": 0.2,
                "capital": 200.0,
                "learned_score": 42.0,
            }
        ],
        decisions={
            "orders": [
                {
                    "action": "BUY",
                    "symbol": "MSFT",
                    "reason": "WATCH_TOP_SELECTION",
                    "capital": 200.0,
                    "learned_score": 42.0,
                }
            ]
        },
    )

    assert data["analysis"]["source"] == "current_run"
    assert data["analysis"]["current_results"][0]["symbol"] == "NVDA"
    assert data["analysis"]["trading_plan"][0]["symbol"] == "MSFT"
    assert data["analysis"]["simulated_portfolio"][0]["wkn"] == "918422"
    assert data["analysis"]["orders"][0]["action"] == "BUY"


def test_build_dashboard_reads_latest_run_snapshot(monkeypatch, tmp_path):
    _patch_dashboard_dependencies(monkeypatch)

    latest_run_path = tmp_path / "latest_run.json"
    latest_run_path.write_text(
        json.dumps(
            {
                "generated_at_utc": "2026-04-03T18:35:40Z",
                "period": "1mo",
                "interval": "5m",
                "results": [
                    {
                        "symbol": "AAPL",
                        "company_name": "Apple Inc.",
                        "isin": "US0378331005",
                        "wkn": "865985",
                        "signal": "BUY",
                        "pnl_eur": 111.0,
                        "trade_count": 4,
                        "score": 55.0,
                    }
                ],
                "future_candidates": [],
                "portfolio": {},
                "trading_plan": [],
                "decisions": {"orders": []},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(dashboard, "LATEST_RUN_JSON", str(latest_run_path))

    data = dashboard.build_dashboard_data()

    assert data["analysis"]["source"] == "latest_run"
    assert data["analysis"]["current_results"][0]["symbol"] == "AAPL"


def test_build_dashboard_writes_html_with_current_analysis(monkeypatch, tmp_path):
    _patch_dashboard_dependencies(monkeypatch)
    monkeypatch.setattr(dashboard, "DASHBOARD_JSON", str(tmp_path / "dashboard_latest.json"))
    monkeypatch.setattr(dashboard, "DASHBOARD_HTML", str(tmp_path / "dashboard_latest.html"))
    monkeypatch.setattr(dashboard, "ensure_reports_dir", lambda: str(tmp_path))

    dashboard.build_dashboard(analysis_result=_sample_analysis_result())

    html = (tmp_path / "dashboard_latest.html").read_text(encoding="utf-8")
    assert "Aktuelle Analyse-Ergebnisse" in html
    assert "NVIDIA Corporation" in html
    assert "US67066G1040" in html
