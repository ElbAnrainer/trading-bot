import walkforward


def test_apply_orders_executes_sell_and_buy_without_mutating_input():
    original_portfolio = {
        "AAA": {
            "entry_price": 10.0,
            "shares": 5.0,
            "capital": 50.0,
            "current_price": 10.0,
        }
    }
    orders = [
        {"symbol": "AAA", "action": "SELL"},
        {"symbol": "BBB", "action": "BUY", "capital": 60.0},
    ]
    prices = {
        "AAA": 12.0,
        "BBB": 20.0,
    }

    portfolio, realized_pnl = walkforward._apply_orders(original_portfolio, orders, prices)

    assert original_portfolio == {
        "AAA": {
            "entry_price": 10.0,
            "shares": 5.0,
            "capital": 50.0,
            "current_price": 10.0,
        }
    }
    assert "AAA" not in portfolio
    assert portfolio["BBB"]["shares"] == 3.0
    assert portfolio["BBB"]["entry_price"] == 20.0
    assert realized_pnl == 10.0


def test_extract_prices_uses_price_close_and_zero_fallback():
    result = {
        "results": [
            {"symbol": "AAA", "price": 11.5},
            {"symbol": "BBB", "close": 9.25},
            {"symbol": "CCC"},
        ]
    }

    assert walkforward._extract_prices(result) == {
        "AAA": 11.5,
        "BBB": 9.25,
        "CCC": 0.0,
    }


def test_run_walk_forward_aggregates_pnl_hit_rate_and_trades(monkeypatch):
    monkeypatch.setattr(walkforward, "WALK_WINDOWS", ["1mo", "3mo"])
    monkeypatch.setattr(walkforward, "get_active_profile_name", lambda: "test-profile")
    monkeypatch.setattr(
        walkforward,
        "get_trading_config",
        lambda profile_name=None: {"initial_capital": 1000.0, "max_positions": 3},
    )

    def fake_run_analysis(period, top_n, min_volume, long_mode, show_progress):
        prices = {
            "1mo": 10.0,
            "3mo": 12.0,
        }
        assert top_n == 3
        assert min_volume == walkforward.DEFAULT_MIN_VOLUME
        return {"results": [{"symbol": "AAA", "price": prices[period]}]}

    def fake_simulate_trading_decisions(
        analysis_result,
        total_capital,
        current_positions,
        peak_equity,
        top_n=None,
        profile_name=None,
    ):
        assert top_n == 3
        assert profile_name == "test-profile"
        if current_positions:
            return {"orders": [{"symbol": "AAA", "action": "SELL"}]}
        return {"orders": [{"symbol": "AAA", "action": "BUY", "capital": 100.0}]}

    monkeypatch.setattr(walkforward, "run_analysis", fake_run_analysis)
    monkeypatch.setattr(walkforward, "simulate_trading_decisions", fake_simulate_trading_decisions)

    result = walkforward.run_walk_forward(total_capital=1000.0)

    assert result["trades"] == 2
    assert result["avg_pnl"] == 10.0
    assert result["hit_rate"] == 50.0
    assert result["profile_name"] == "test-profile"
    assert [point["equity"] for point in result["equity_curve"]] == [1000.0, 1020.0]
