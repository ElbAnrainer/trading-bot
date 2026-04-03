import dashboard_live as dl


def _sample_data():
    return {
        "analysis": {
            "period": "1mo",
            "interval": "5m",
            "generated_at": "2026-04-03T10:30:00Z",
            "current_results": [
                {
                    "symbol": "AAPL",
                    "isin": "US0378331005",
                    "wkn": "865985",
                    "signal": "BUY",
                    "pnl_eur": 123.45,
                    "trade_count": 9,
                    "score": 72.5,
                }
            ],
            "trading_plan": [
                {
                    "symbol": "MSFT",
                    "isin": "US5949181045",
                    "wkn": "870747",
                    "weight": 0.35,
                    "capital": 3500.0,
                    "learned_score": 42.0,
                }
            ],
            "future_candidates": [],
            "simulated_portfolio": [],
            "orders": [],
        },
        "performance": {
            "ranking": [
                {
                    "symbol": "AAPL",
                    "isin": "US0378331005",
                    "wkn": "865985",
                    "bonus": 1.25,
                    "hit_rate": 61.5,
                    "avg_pnl": 123.45,
                    "trades": 9,
                }
            ],
            "portfolio_plan": [
                {
                    "symbol": "MSFT",
                    "isin": "US5949181045",
                    "wkn": "870747",
                    "weight": 0.35,
                    "capital": 3500.0,
                    "learned_score": 42.0,
                }
            ],
            "closed_trades": 12,
            "hit_rate": 58.3,
            "realized_pnl": 245.0,
            "avg_trade_pnl": 20.42,
        },
        "state": {
            "cash_eur": 4400.0,
            "total_invested_eur": 5600.0,
            "last_equity_eur": 10000.0,
            "peak_equity_eur": 10250.0,
            "drawdown_pct": -2.44,
            "positions": 2,
            "updated_at": "2026-04-03 10:15:00",
            "open_positions": {
                "MSFT": {
                    "isin": "US5949181045",
                    "wkn": "870747",
                    "entry_price": 312.0,
                    "current_price": 318.0,
                    "shares": 5.5,
                    "invested_eur": 1716.0,
                }
            },
            "history_tail": [
                {
                    "time": "2026-04-03 10:00",
                    "type": "BUY",
                    "symbol": "MSFT",
                    "isin": "US5949181045",
                    "wkn": "870747",
                    "price": 312.0,
                    "reason": "Breakout",
                }
            ],
        },
    }


def test_build_live_terminal_lines_uses_two_columns_on_wide_terminals(monkeypatch):
    monkeypatch.setattr(dl, "get_active_profile_name", lambda: "konservativ")
    monkeypatch.setattr(
        dl,
        "get_trading_config",
        lambda name: {
            "max_positions": 5,
            "risk_per_trade_pct": 0.01,
            "max_portfolio_risk_pct": 0.05,
            "min_hold_bars": 3,
            "cooldown_bars": 2,
            "max_new_trades_per_week": 4,
            "min_expected_edge_pct": 0.02,
        },
    )

    lines = dl._build_live_terminal_lines(_sample_data(), "2026-04-03 10:30:00", width=160)
    clean = [dl._strip_ansi(line) for line in lines]

    assert any("AKTIVER ANALYSE-LAUF" in line or "AKTUELLER ANALYSE-LAUF" in line for line in clean)
    assert any("HISTORISCHE PERFORMANCE" in line for line in clean)
    assert any("MINI-SYSTEM-STATUS" in line for line in clean)
    assert any("US0378331005" in line for line in clean)
    assert max(len(line) for line in clean) <= 160


def test_build_live_terminal_lines_stacks_sections_on_narrow_terminals(monkeypatch):
    monkeypatch.setattr(dl, "get_active_profile_name", lambda: "konservativ")
    monkeypatch.setattr(
        dl,
        "get_trading_config",
        lambda name: {
            "max_positions": 5,
            "risk_per_trade_pct": 0.01,
            "max_portfolio_risk_pct": 0.05,
            "min_hold_bars": 3,
            "cooldown_bars": 2,
            "max_new_trades_per_week": 4,
            "min_expected_edge_pct": 0.02,
        },
    )

    lines = dl._build_live_terminal_lines(_sample_data(), "2026-04-03 10:30:00", width=100)
    clean = [dl._strip_ansi(line) for line in lines]

    profile_idx = next(i for i, line in enumerate(clean) if "AKTIVES PROFIL" in line)
    portfolio_idx = next(i for i, line in enumerate(clean) if "AKTUELLER TRADING-PLAN" in line)

    assert portfolio_idx > profile_idx
    assert not any("AKTIVES PROFIL" in line and "AKTUELLER TRADING-PLAN" in line for line in clean)
    assert any("865985" in line for line in clean)
    assert max(len(line) for line in clean) <= 100
