import pandas as pd

from strategy import (
    _risk_label,
    add_signals,
    compute_qty,
    normalize_signal_from_row,
    stop_loss_price,
    take_profit_price,
    analyze_symbol,
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


def test_analyze_symbol_contains_future_fields():
    df = make_df()
    out = analyze_symbol(df, "AAPL")

    assert out is not None
    assert "future_signal" in out
    assert "strength" in out
    assert "risk" in out
    assert "reasons" in out


def test_add_signals_stores_volatility_20_as_decimal():
    closes = [100.0]
    for idx in range(1, 60):
        closes.append(closes[-1] * (1.04 if idx % 2 else 0.96))

    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [value * 1.01 for value in closes],
            "Low": [value * 0.99 for value in closes],
            "Close": closes,
            "Volume": [10_000_000] * len(closes),
        }
    )

    out = add_signals(df)
    latest_volatility = float(out["volatility_20"].dropna().iloc[-1])

    assert 0.02 < latest_volatility < 0.06


def test_risk_label_uses_decimal_volatility_thresholds():
    assert _risk_label(0.05, 0.0) == "hoch"
    assert _risk_label(0.03, 0.0) == "mittel"
    assert _risk_label(0.01, 0.0) == "niedrig"
