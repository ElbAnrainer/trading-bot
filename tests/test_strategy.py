import pandas as pd

from strategy import add_signals, normalize_signal, compute_qty


def test_normalize_signal():
    assert normalize_signal(1) == "BUY"
    assert normalize_signal(-1) == "SELL"
    assert normalize_signal(0) == "HOLD"


def test_compute_qty_from_cash_and_price():
    qty = compute_qty(10000.0, 250.0)
    assert qty == 4


def test_compute_qty_returns_zero_if_price_too_high():
    qty = compute_qty(100.0, 1000.0)
    assert qty == 0


def test_add_signals_adds_expected_columns():
    df = pd.DataFrame({
        "Open": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
        "High": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
        "Low":  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
        "Close":[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
        "Volume":[100]*21,
    })

    out = add_signals(df)

    assert "sma_fast" in out.columns
    assert "sma_slow" in out.columns
    assert "signal" in out.columns


def test_add_signals_produces_buy_signal_on_rising_data():
    df = pd.DataFrame({
        "Open": list(range(1, 31)),
        "High": list(range(1, 31)),
        "Low": list(range(1, 31)),
        "Close": list(range(1, 31)),
        "Volume": [100] * 30,
    })

    out = add_signals(df)
    last_signal = int(out.iloc[-1]["signal"])

    assert last_signal == 1
