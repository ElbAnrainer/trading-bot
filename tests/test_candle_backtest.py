import pandas as pd

import candle_backtest as cb


def test_evaluate_open_position_uses_profile_stop_loss(monkeypatch):
    monkeypatch.setattr(
        cb,
        "latest_signal",
        lambda df: {"signal": "HOLD", "price": 93.0, "time": "2026-04-03T10:00:00"},
    )

    position = {
        "entry_price": 100.0,
        "highest_price": 100.0,
    }

    conservative = cb.evaluate_open_position(position, pd.DataFrame(), profile_name="konservativ")
    offensive = cb.evaluate_open_position(position, pd.DataFrame(), profile_name="offensiv")

    assert conservative["action"] == "HOLD"
    assert offensive["action"] == "SELL"
    assert offensive["reason"] == "STOP_LOSS"


def test_evaluate_open_position_uses_profile_trailing_stop(monkeypatch):
    monkeypatch.setattr(
        cb,
        "latest_signal",
        lambda df: {"signal": "HOLD", "price": 90.5, "time": "2026-04-03T10:00:00"},
    )

    position = {
        "entry_price": 80.0,
        "highest_price": 100.0,
    }

    conservative = cb.evaluate_open_position(position, pd.DataFrame(), profile_name="konservativ")
    offensive = cb.evaluate_open_position(position, pd.DataFrame(), profile_name="offensiv")

    assert conservative["action"] == "HOLD"
    assert offensive["action"] == "SELL"
    assert offensive["reason"] == "TRAILING_STOP"
