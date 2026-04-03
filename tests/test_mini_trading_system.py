from datetime import datetime as RealDateTime
from types import SimpleNamespace

import pandas as pd

import mini_trading_system as mts


class FixedDateTime(RealDateTime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 4, 2, 12, 0, 0)


def _config() -> dict:
    return {
        "initial_capital": 1000.0,
        "max_positions": 1,
        "min_hold_days": 3,
        "cooldown_days": 5,
        "max_new_trades_per_run": 1,
        "max_new_trades_per_week": 2,
        "min_learned_score": 0.0,
        "max_volatility_20": 1.0,
        "min_expected_edge_pct": 0.0,
        "fee_pct": 0.0,
        "slippage_pct": 0.0,
        "risk_per_trade_pct": 0.1,
        "max_position_pct": 0.5,
        "vol_target": 0.02,
        "stop_loss_pct": 0.08,
        "trailing_stop_pct": 0.10,
        "adaptive_stop_min_pct": 0.05,
        "adaptive_stop_max_pct": 0.20,
        "adaptive_trailing_min_pct": 0.07,
        "adaptive_trailing_max_pct": 0.15,
        "min_trade_eur": 50.0,
        "max_new_trades_per_week": 2,
    }


def _patch_state_helpers(monkeypatch):
    monkeypatch.setattr(mts, "cash_balance", lambda state: float(state.get("cash", 0.0)))
    monkeypatch.setattr(mts, "current_positions", lambda state: state.setdefault("positions", {}))
    monkeypatch.setattr(mts, "set_cash_balance", lambda state, value: state.__setitem__("cash", float(value)))
    monkeypatch.setattr(
        mts,
        "set_position",
        lambda state, symbol, pos: state.setdefault("positions", {}).__setitem__(symbol, pos),
    )
    monkeypatch.setattr(
        mts,
        "remove_position",
        lambda state, symbol: state.setdefault("positions", {}).pop(symbol, None),
    )
    monkeypatch.setattr(
        mts,
        "append_history_event",
        lambda state, event: state.setdefault("history", []).append(event),
    )

    def fake_update_equity(state, equity):
        peak = float(state.get("peak_equity_eur", equity))
        state["peak_equity_eur"] = max(peak, float(equity))

    monkeypatch.setattr(mts, "update_equity", fake_update_equity)
    monkeypatch.setattr(mts, "save_portfolio_state", lambda state: state.__setitem__("_saved", True))


def test_days_since_exit_and_trades_this_week_support_bar_time(monkeypatch):
    monkeypatch.setattr(mts, "datetime", FixedDateTime)

    state = {
        "history": [
            {"type": "BUY", "symbol": "AAA", "bar_time": "2026-04-01T10:00:00"},
            {"type": "BUY", "symbol": "BBB", "time": "2026-03-20T10:00:00"},
            {"type": "SELL", "symbol": "AAA", "bar_time": "2026-04-02T11:00:00"},
        ]
    }

    assert mts._days_since_exit(state, "AAA") == 0
    assert mts._trades_this_week(state) == 1


def test_mark_to_market_equity_uses_latest_close_and_entry_fallback(monkeypatch):
    _patch_state_helpers(monkeypatch)
    state = {
        "cash": 100.0,
        "positions": {
            "AAA": {"shares": 2.0, "entry_price": 100.0},
            "BBB": {"shares": 3.0, "entry_price": 50.0},
        },
    }
    market_data = {
        "AAA": pd.DataFrame({"Close": [110.0]}),
    }

    equity = mts._mark_to_market_equity(state, market_data)

    assert equity == 470.0


def test_row_volatility_normalizes_legacy_percentage_values():
    assert mts._row_volatility({"volatility_20": 3.0}) == 0.03


def test_run_mini_trading_system_records_buy_event_with_time(monkeypatch):
    monkeypatch.setattr(mts, "datetime", FixedDateTime)
    _patch_state_helpers(monkeypatch)

    state = {"cash": 1000.0, "positions": {}, "history": []}
    market_df = pd.DataFrame(
        {"Close": [100.0], "volatility_20": [0.02], "momentum_20": [0.05]},
        index=pd.to_datetime(["2026-04-02"]),
    )

    monkeypatch.setattr(mts, "get_trading_config", lambda profile_name=None: _config())
    monkeypatch.setattr(mts, "get_active_profile_name", lambda: "test-profile")
    monkeypatch.setattr(mts, "load_portfolio_state", lambda initial_cash=1000.0: state)
    monkeypatch.setattr(mts, "analyze_performance", lambda: {"ranking": []})
    monkeypatch.setattr(
        mts,
        "build_trading_plan",
        lambda total_capital=1000.0, top_n=1, profile_name=None: [
            {"symbol": "AAA", "learned_score": 25.0, "isin": "US0000000001", "wkn": "AAA111"}
        ],
    )
    monkeypatch.setattr(mts, "_fetch_all", lambda symbols, period, interval: {"AAA": market_df})
    monkeypatch.setattr(
        mts,
        "may_open_new_positions",
        lambda current_equity, peak_equity=None, profile_name=None: (
            True,
            SimpleNamespace(trading_blocked=False),
        ),
    )
    monkeypatch.setattr(mts, "latest_signal", lambda df: {"signal": "BUY", "price": 100.0, "time": "2026-04-02T10:00:00"})
    monkeypatch.setattr(mts, "adaptive_stop_loss_pct", lambda *args: 0.08)
    monkeypatch.setattr(mts, "adaptive_trailing_stop_pct", lambda *args: 0.10)
    monkeypatch.setattr(
        mts,
        "calculate_position_budget_from_risk",
        lambda **kwargs: {"shares": 2.0, "invested_eur": 200.0, "risk_amount_eur": 16.0},
    )

    result = mts.run_mini_trading_system()

    assert result["orders"] == [
        {"action": "BUY", "symbol": "AAA", "capital": 200.0, "reason": "BUY_SIGNAL_TOP_SELECTION"}
    ]
    assert state["cash"] == 800.0
    assert state["positions"]["AAA"]["opened_at"] == "2026-04-02T10:00:00"
    assert state["positions"]["AAA"]["isin"] == "US0000000001"
    assert state["history"][0]["wkn"] == "AAA111"
    assert state["history"][0]["time"] == "2026-04-02T10:00:00"
    assert mts._trades_this_week(state) == 1
    assert state["_saved"] is True


def test_run_mini_trading_system_records_sell_event_with_time(monkeypatch):
    monkeypatch.setattr(mts, "datetime", FixedDateTime)
    _patch_state_helpers(monkeypatch)

    state = {
        "cash": 100.0,
        "positions": {
            "AAA": {
                "symbol": "AAA",
                "isin": "US0000000001",
                "wkn": "AAA111",
                "entry_price": 100.0,
                "current_price": 100.0,
                "highest_price": 100.0,
                "shares": 2.0,
                "invested_eur": 200.0,
                "opened_at": "2026-03-20T10:00:00",
            }
        },
        "history": [],
    }
    market_df = pd.DataFrame({"Close": [110.0]}, index=pd.to_datetime(["2026-04-02"]))

    monkeypatch.setattr(mts, "get_trading_config", lambda profile_name=None: _config())
    monkeypatch.setattr(mts, "get_active_profile_name", lambda: "test-profile")
    monkeypatch.setattr(mts, "load_portfolio_state", lambda initial_cash=1000.0: state)
    monkeypatch.setattr(mts, "analyze_performance", lambda: {"ranking": []})
    monkeypatch.setattr(mts, "build_trading_plan", lambda total_capital=1000.0, top_n=1, profile_name=None: [])
    monkeypatch.setattr(mts, "_fetch_all", lambda symbols, period, interval: {"AAA": market_df})
    monkeypatch.setattr(
        mts,
        "may_open_new_positions",
        lambda current_equity, peak_equity=None, profile_name=None: (
            True,
            SimpleNamespace(trading_blocked=False),
        ),
    )
    monkeypatch.setattr(
        mts,
        "evaluate_open_position",
        lambda pos, df: {
            "action": "SELL",
            "reason": "SELL_SIGNAL",
            "price": 110.0,
            "time": "2026-04-02T11:00:00",
            "highest_price": 115.0,
        },
    )

    result = mts.run_mini_trading_system()

    assert result["orders"] == [
        {"action": "SELL", "symbol": "AAA", "capital": 220.0, "reason": "SELL_SIGNAL"}
    ]
    assert state["positions"] == {}
    assert state["cash"] == 320.0
    assert state["history"][0]["isin"] == "US0000000001"
    assert state["history"][0]["time"] == "2026-04-02T11:00:00"
    assert mts._days_since_exit(state, "AAA") == 0


def test_run_mini_trading_system_keeps_position_when_sell_signal_too_early(monkeypatch):
    monkeypatch.setattr(mts, "datetime", FixedDateTime)
    _patch_state_helpers(monkeypatch)

    state = {
        "cash": 100.0,
        "positions": {
            "AAA": {
                "symbol": "AAA",
                "entry_price": 100.0,
                "current_price": 100.0,
                "highest_price": 100.0,
                "shares": 2.0,
                "invested_eur": 200.0,
                "opened_at": "2026-04-01T10:00:00",
            }
        },
        "history": [],
    }
    market_df = pd.DataFrame({"Close": [101.0]}, index=pd.to_datetime(["2026-04-02"]))

    monkeypatch.setattr(mts, "get_trading_config", lambda profile_name=None: _config())
    monkeypatch.setattr(mts, "get_active_profile_name", lambda: "test-profile")
    monkeypatch.setattr(mts, "load_portfolio_state", lambda initial_cash=1000.0: state)
    monkeypatch.setattr(mts, "analyze_performance", lambda: {"ranking": []})
    monkeypatch.setattr(mts, "build_trading_plan", lambda total_capital=1000.0, top_n=1, profile_name=None: [])
    monkeypatch.setattr(mts, "_fetch_all", lambda symbols, period, interval: {"AAA": market_df})
    monkeypatch.setattr(
        mts,
        "may_open_new_positions",
        lambda current_equity, peak_equity=None, profile_name=None: (
            True,
            SimpleNamespace(trading_blocked=False),
        ),
    )
    monkeypatch.setattr(
        mts,
        "evaluate_open_position",
        lambda pos, df: {
            "action": "SELL",
            "reason": "SELL_SIGNAL",
            "price": 101.0,
            "time": "2026-04-02T09:00:00",
            "highest_price": 103.0,
        },
    )

    result = mts.run_mini_trading_system()

    assert result["orders"] == []
    assert "AAA" in state["positions"]
    assert state["positions"]["AAA"]["current_price"] == 101.0
    assert state["positions"]["AAA"]["highest_price"] == 103.0
    assert state["history"] == []
