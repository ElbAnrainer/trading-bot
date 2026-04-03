import pytest

import risk


def _profile(**overrides):
    cfg = {
        "max_position_pct": 0.25,
        "stop_loss_pct": 0.08,
        "trailing_stop_pct": 0.10,
        "max_drawdown_pct": 0.15,
        "min_trade_eur": 250.0,
    }
    cfg.update(overrides)
    return cfg


def test_risk_summary_uses_profile_values(monkeypatch):
    monkeypatch.setattr(
        risk,
        "get_trading_config",
        lambda profile_name=None: _profile(
            max_position_pct=0.35,
            stop_loss_pct=0.11,
            trailing_stop_pct=0.13,
            max_drawdown_pct=0.09,
            min_trade_eur=120.0,
        ),
    )

    summary = risk.risk_summary("test")

    assert summary == {
        "max_position_pct": 0.35,
        "stop_loss_pct": 0.11,
        "trailing_stop_pct": 0.13,
        "max_drawdown_pct": 0.09,
        "min_position_eur": 120.0,
    }


def test_may_open_new_positions_blocks_on_profile_drawdown(monkeypatch):
    monkeypatch.setattr(
        risk,
        "get_trading_config",
        lambda profile_name=None: _profile(max_drawdown_pct=0.10),
    )

    allowed, state = risk.may_open_new_positions(
        current_equity=880.0,
        peak_equity=1000.0,
        profile_name="test",
    )

    assert allowed is False
    assert state.trading_blocked is True
    assert state.drawdown_pct == pytest.approx(0.12)
