import pandas as pd

from strategy import (
    add_signals,
    compute_qty,
    normalize_signal_from_row,
    stop_loss_price,
    take_profit_price,
)


def make_df(rows=260):
    base = list(range(1, rows + 1))
    return pd.DataFrame(
        {
            "Open": base,
            "High": [x + 1 for x in base],
            "Low": [x - 1 for x in base],
            "Close": base,
            "Volume": [10_000_000] * rows,
        }
    )


def test_add_signals_creates_expected_columns():
    df = make_df()
    out = add_signals(df)

    expected = {
        "ema_fast",
        "ema_slow",
        "rsi",
        "sma_trend",
        "atr",
        "atr_pct",
        "breakout_high",
        "breakout_low",
        "trend_ok",
        "volatility_ok",
        "momentum_ok",
        "breakout_ok",
        "buy_signal",
        "sell_signal",
    }

    assert expected.issubset(set(out.columns))


def test_compute_qty_returns_positive_for_normal_case():
    qty = compute_qty(10_000.0, 100.0)
    assert qty > 0


def test_compute_qty_returns_zero_for_invalid_price():
    assert compute_qty(10_000.0, 0.0) == 0
    assert compute_qty(10_000.0, -5.0) == 0


def test_stop_loss_price():
    assert stop_loss_price(100.0) < 100.0


def test_take_profit_price():
    assert take_profit_price(100.0) > 100.0


def test_normalize_signal_from_row_buy():
    row = {
        "buy_signal": True,
        "sell_signal": False,
    }
    assert normalize_signal_from_row(row) == "BUY"


def test_normalize_signal_from_row_sell():
    row = {
        "buy_signal": False,
        "sell_signal": True,
    }
    assert normalize_signal_from_row(row) == "SELL"


def test_normalize_signal_from_row_hold():
    row = {
        "buy_signal": False,
        "sell_signal": False,
    }
    assert normalize_signal_from_row(row) == "HOLD"
