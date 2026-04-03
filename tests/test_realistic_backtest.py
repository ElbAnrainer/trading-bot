import json

import pandas as pd
import pytest

import realistic_backtest as rb


def _test_config() -> dict:
    return {
        "initial_capital": 1000.0,
        "max_positions": 1,
        "fee_pct": 0.0,
        "slippage_pct": 0.0,
        "stop_loss_pct": 0.10,
        "trailing_stop_pct": 0.20,
        "min_trade_eur": 50.0,
        "min_hold_bars": 0,
        "cooldown_bars": 0,
        "max_new_trades_per_bar": 1,
        "max_new_trades_per_week": 2,
        "min_learned_score": 0.0,
        "max_volatility_20": 1.0,
        "min_stop_distance_pct": 0.01,
        "min_expected_edge_pct": 0.0,
        "risk_per_trade_pct": 0.10,
        "max_position_pct": 0.50,
        "max_portfolio_risk_pct": 1.0,
        "vol_target": 0.02,
        "adaptive_stop_min_pct": 0.05,
        "adaptive_stop_max_pct": 0.20,
        "adaptive_trailing_min_pct": 0.10,
        "adaptive_trailing_max_pct": 0.30,
    }


def _position(symbol: str, shares: float, entry_price: float) -> rb.OpenPosition:
    return rb.OpenPosition(
        symbol=symbol,
        shares=shares,
        entry_price=entry_price,
        highest_price=entry_price,
        invested_eur=shares * entry_price,
        entry_date="2026-01-05",
        entry_bar_index=0,
        stop_loss_pct=0.10,
        trailing_stop_pct=0.20,
        risk_amount_eur=10.0,
    )


def test_flatten_columns_flattens_multiindex():
    df = pd.DataFrame(
        [[100.0, 1_000]],
        columns=pd.MultiIndex.from_tuples([("Close", "AAA"), ("Volume", "AAA")]),
    )

    flattened = rb._flatten_columns(df)

    assert list(flattened.columns) == ["Close", "Volume"]


def test_build_calendar_merges_dates_in_sorted_order():
    data = {
        "AAA": pd.DataFrame(index=pd.to_datetime(["2026-01-06", "2026-01-05"])),
        "BBB": pd.DataFrame(index=pd.to_datetime(["2026-01-07"])),
    }

    calendar = rb._build_calendar(data)

    assert calendar == list(pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-07"]))


def test_mark_to_market_equity_uses_close_and_entry_price_fallback():
    positions = {
        "AAA": _position("AAA", shares=2.0, entry_price=100.0),
        "BBB": _position("BBB", shares=3.0, entry_price=50.0),
    }
    candle_rows = {
        "AAA": pd.Series({"Close": 110.0}),
    }

    equity = rb._mark_to_market_equity(100.0, positions, candle_rows)

    assert equity == 470.0


def test_drawdown_and_edge_helpers_cover_core_math():
    curve = [
        {"equity_eur": 100.0},
        {"equity_eur": 120.0},
        {"equity_eur": 90.0},
        {"equity_eur": 130.0},
    ]
    row = pd.Series({"volatility_20": 0.03, "momentum_20": 0.05})

    assert rb._max_drawdown_pct(curve) == 25.0
    assert rb._annualized_return(0.0, 120.0, 365) == 0.0
    assert rb._row_volatility(row) == 0.03
    assert rb._expected_edge_pct(row, stop_loss_pct=0.08, fee_pct=0.001, slippage_pct=0.001) == pytest.approx(0.038)


def test_row_volatility_normalizes_legacy_percentage_values():
    row = pd.Series({"volatility_20": 3.0})

    assert rb._row_volatility(row) == 0.03


def test_pick_symbols_falls_back_to_performance_ranking(monkeypatch):
    monkeypatch.setattr(
        rb,
        "analyze_performance",
        lambda: {"ranking": [{"symbol": "AAA"}, {"symbol": "BBB"}, {"symbol": ""}]},
    )

    assert rb._pick_symbols(None, top_n=2) == ["AAA", "BBB"]
    assert rb._pick_symbols(["MSFT", "", None], top_n=3) == ["MSFT"]


def test_run_realistic_backtest_returns_note_when_no_market_data(monkeypatch, tmp_path):
    latest_json = tmp_path / "realistic_backtest_latest.json"

    monkeypatch.setattr(rb, "REPORTS_DIR", str(tmp_path))
    monkeypatch.setattr(rb, "LATEST_JSON", str(latest_json))
    monkeypatch.setattr(rb, "get_trading_config", lambda profile_name=None: _test_config())
    monkeypatch.setattr(rb, "get_active_profile_name", lambda: "test-profile")
    monkeypatch.setattr(rb, "_pick_symbols", lambda symbols, top_n: ["AAA"])
    monkeypatch.setattr(rb, "_score_lookup", lambda: {"AAA": 25.0})
    monkeypatch.setattr(rb, "_fetch_market_data", lambda symbols, period, interval: {})

    result = rb.run_realistic_backtest(period="6mo")

    assert result["note"] == "Keine Daten verfügbar."
    assert result["symbols"] == []
    assert result["final_equity"] == 1000.0
    assert json.loads(latest_json.read_text(encoding="utf-8"))["note"] == "Keine Daten verfügbar."


def test_run_realistic_backtest_executes_single_profitable_trade(monkeypatch, tmp_path):
    latest_json = tmp_path / "realistic_backtest_latest.json"
    data = pd.DataFrame(
        {
            "Close": [100.0, 110.0, 105.0],
            "buy_signal": [True, False, False],
            "sell_signal": [False, False, True],
            "volatility_20": [0.02, 0.02, 0.02],
            "momentum_20": [0.05, 0.05, 0.05],
        },
        index=pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-07"]),
    )

    monkeypatch.setattr(rb, "REPORTS_DIR", str(tmp_path))
    monkeypatch.setattr(rb, "LATEST_JSON", str(latest_json))
    monkeypatch.setattr(rb, "get_trading_config", lambda profile_name=None: _test_config())
    monkeypatch.setattr(rb, "get_active_profile_name", lambda: "test-profile")
    monkeypatch.setattr(rb, "_pick_symbols", lambda symbols, top_n: ["AAA"])
    monkeypatch.setattr(rb, "_score_lookup", lambda: {"AAA": 50.0})
    monkeypatch.setattr(rb, "_fetch_market_data", lambda symbols, period, interval: {"AAA": data})

    result = rb.run_realistic_backtest(period="1y")

    assert result["symbols"] == ["AAA"]
    assert result["trade_count"] == 1
    assert result["win_rate_pct"] == 100.0
    assert result["final_equity"] == 1025.0
    assert result["total_return_pct"] == 2.5
    assert result["max_drawdown_pct"] == pytest.approx(2.38, abs=0.01)
    assert len(result["equity_curve"]) == 3
    assert result["trades"][0]["reason"] == "SELL_SIGNAL"
    assert result["trades"][0]["pnl_eur"] == 25.0

    saved = json.loads(latest_json.read_text(encoding="utf-8"))
    assert saved["final_equity"] == 1025.0
    assert saved["trade_count"] == 1
