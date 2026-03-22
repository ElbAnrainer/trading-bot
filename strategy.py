import pandas as pd

from config import (
    RISK_PER_TRADE_PCT,
    MAX_ALLOC_PCT,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    EMA_FAST,
    EMA_SLOW,
    RSI_PERIOD,
    RSI_BUY_MIN,
    RSI_BUY_MAX,
    RSI_SELL_MIN,
    TREND_SMA,
    BREAKOUT_LOOKBACK,
    ATR_PERIOD,
    MIN_ATR_PCT,
)


def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)

    ma_up = up.ewm(alpha=1 / period, adjust=False).mean()
    ma_down = down.ewm(alpha=1 / period, adjust=False).mean()

    rs = ma_up / ma_down.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))


def atr(df, period=14):
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift(1)).abs()
    low_close = (df["Low"] - df["Close"].shift(1)).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def add_signals(df):
    df = df.copy()

    df["ema_fast"] = ema(df["Close"], EMA_FAST)
    df["ema_slow"] = ema(df["Close"], EMA_SLOW)
    df["rsi"] = rsi(df["Close"], RSI_PERIOD)
    df["sma_trend"] = df["Close"].rolling(TREND_SMA).mean()
    df["atr"] = atr(df, ATR_PERIOD)
    df["atr_pct"] = (df["atr"] / df["Close"]) * 100

    df["breakout_high"] = df["High"].rolling(BREAKOUT_LOOKBACK).max().shift(1)
    df["breakout_low"] = df["Low"].rolling(BREAKOUT_LOOKBACK).min().shift(1)

    df["trend_ok"] = df["Close"] > df["sma_trend"]
    df["volatility_ok"] = df["atr_pct"] >= MIN_ATR_PCT
    df["momentum_ok"] = (
        (df["ema_fast"] > df["ema_slow"])
        & (df["rsi"] >= RSI_BUY_MIN)
        & (df["rsi"] <= RSI_BUY_MAX)
    )
    df["breakout_ok"] = df["Close"] > df["breakout_high"]

    df["buy_signal"] = (
        df["trend_ok"]
        & df["volatility_ok"]
        & df["momentum_ok"]
        & df["breakout_ok"]
    )

    df["sell_signal"] = (
        (df["ema_fast"] < df["ema_slow"])
        | (df["rsi"] < RSI_SELL_MIN)
        | (df["Close"] < df["breakout_low"])
    )

    return df


def normalize_signal_from_row(row):
    if bool(row.get("buy_signal", False)):
        return "BUY"
    if bool(row.get("sell_signal", False)):
        return "SELL"
    return "HOLD"


def compute_qty(cash, price):
    """
    Dynamische Positionsgröße:
    - Risiko pro Trade = cash * RISK_PER_TRADE_PCT
    - Maximalinvestition = cash * MAX_ALLOC_PCT
    - Stückzahl wird durch das engere Limit begrenzt
    """
    if price <= 0:
        return 0

    risk_budget = cash * RISK_PER_TRADE_PCT
    max_alloc_budget = cash * MAX_ALLOC_PCT

    risk_per_share = price * STOP_LOSS_PCT
    if risk_per_share <= 0:
        return 0

    qty_risk = int(risk_budget // risk_per_share)
    qty_alloc = int(max_alloc_budget // price)

    qty = min(qty_risk, qty_alloc)
    return max(qty, 0)


def stop_loss_price(entry_price):
    return entry_price * (1 - STOP_LOSS_PCT)


def take_profit_price(entry_price):
    return entry_price * (1 + TAKE_PROFIT_PCT)


def analyze_symbol(df, symbol):
    if df is None or df.empty or len(df) < max(TREND_SMA, BREAKOUT_LOOKBACK, 30):
        return None

    df = add_signals(df)

    last = df.iloc[-1]

    if pd.isna(last["atr_pct"]) or pd.isna(last["rsi"]) or pd.isna(last["sma_trend"]):
        return None

    momentum = ((last["Close"] / df["Close"].iloc[-20]) - 1) * 100 if len(df) >= 20 else 0.0
    volatility = float(last["atr_pct"])
    avg_volume = float(df["Volume"].tail(20).mean())

    score = (
        momentum * 0.45
        + volatility * 15
        + (10 if bool(last["trend_ok"]) else 0)
        + (8 if bool(last["breakout_ok"]) else 0)
        + (5 if bool(last["momentum_ok"]) else 0)
    )

    is_candidate = bool(last["trend_ok"]) and bool(last["volatility_ok"])

    return {
        "symbol": symbol,
        "momentum": momentum,
        "volatility": volatility,
        "avg_volume": avg_volume,
        "score": score,
        "is_candidate": is_candidate,
    }
