import risk
import trading_engine as te


def _profile(**overrides):
    cfg = {
        "max_positions": 5,
        "max_position_pct": 0.25,
        "min_trade_eur": 100.0,
        "stop_loss_pct": 0.08,
        "trailing_stop_pct": 0.10,
        "max_drawdown_pct": 0.15,
    }
    cfg.update(overrides)
    return cfg


def test_build_trading_plan_respects_profile_position_caps(monkeypatch):
    ranking = [
        {"symbol": "AAA", "learned_score": 100.0},
        {"symbol": "BBB", "learned_score": 50.0},
        {"symbol": "CCC", "learned_score": 25.0},
    ]
    cfg = _profile(max_positions=2, max_position_pct=0.25, min_trade_eur=100.0)

    monkeypatch.setattr(te, "analyze_performance", lambda: {"ranking": ranking, "realized_pnl": 0.0})
    monkeypatch.setattr(te, "get_trading_config", lambda profile_name=None: cfg)
    monkeypatch.setattr(risk, "get_trading_config", lambda profile_name=None: cfg)

    plan = te.build_trading_plan(total_capital=1000.0, top_n=5, profile_name="test")

    assert [item["symbol"] for item in plan] == ["AAA", "BBB"]
    assert all(item["capital"] <= 250.0 for item in plan)
    assert all(item["capital"] >= 100.0 for item in plan)


def test_simulate_trading_decisions_uses_profile_stop_loss(monkeypatch):
    ranking = [
        {"symbol": "AAA", "learned_score": 40.0},
    ]
    cfg = _profile(max_positions=1, stop_loss_pct=0.15, max_position_pct=0.50)

    monkeypatch.setattr(te, "analyze_performance", lambda: {"ranking": ranking, "realized_pnl": 0.0})
    monkeypatch.setattr(te, "get_trading_config", lambda profile_name=None: cfg)
    monkeypatch.setattr(risk, "get_trading_config", lambda profile_name=None: cfg)

    decisions = te.simulate_trading_decisions(
        analysis_result={
            "future_candidates": [
                {"symbol": "AAA", "future_signal": "BUY"},
            ]
        },
        total_capital=1000.0,
        current_positions={
            "AAA": {
                "entry_price": 100.0,
                "current_price": 90.0,
                "capital": 400.0,
            }
        },
        peak_equity=1000.0,
        top_n=1,
        profile_name="test",
    )

    assert decisions["orders"] == []
    assert decisions["risk"]["stop_loss_pct"] == 0.15


def test_simulate_trading_decisions_blocks_new_buys_on_profile_drawdown(monkeypatch):
    ranking = [
        {"symbol": "AAA", "learned_score": 40.0},
    ]
    cfg = _profile(max_positions=1, max_drawdown_pct=0.10, max_position_pct=0.50)

    monkeypatch.setattr(te, "analyze_performance", lambda: {"ranking": ranking, "realized_pnl": -120.0})
    monkeypatch.setattr(te, "get_trading_config", lambda profile_name=None: cfg)
    monkeypatch.setattr(risk, "get_trading_config", lambda profile_name=None: cfg)

    decisions = te.simulate_trading_decisions(
        analysis_result={
            "future_candidates": [
                {"symbol": "AAA", "future_signal": "BUY"},
            ]
        },
        total_capital=1000.0,
        current_positions={},
        peak_equity=1000.0,
        top_n=1,
        profile_name="test",
    )

    assert decisions["orders"] == []
    assert decisions["drawdown_state"]["trading_blocked"] is True
    assert decisions["risk"]["max_drawdown_pct"] == 0.10
