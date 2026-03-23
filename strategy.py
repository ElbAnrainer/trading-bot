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
    MIN_SCORE_FOR_BUY,
    MIN_SCORE_FOR_WATCH,
    RELATIVE_STRENGTH_LOOKBACK,
    MIN_RELATIVE_STRENGTH_PCT,
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


def compute_qty(cash_eur, price_eur):
    if price_eur <= 0:
        return 0

    risk_budget = cash_eur * RISK_PER_TRADE_PCT
    max_alloc_budget = cash_eur * MAX_ALLOC_PCT

    risk_per_share = price_eur * STOP_LOSS_PCT
    if risk_per_share <= 0:
        return 0

    qty_risk = int(risk_budget // risk_per_share)
    qty_alloc = int(max_alloc_budget // price_eur)

    qty = min(qty_risk, qty_alloc)
    return max(qty, 0)


def stop_loss_price(entry_price):
    return entry_price * (1 - STOP_LOSS_PCT)


def take_profit_price(entry_price):
    return entry_price * (1 + TAKE_PROFIT_PCT)


def _risk_level(atr_pct, rsi_value):
    if pd.isna(atr_pct) or pd.isna(rsi_value):
        return "mittel"

    if atr_pct >= 3.0 or rsi_value >= 75:
        return "hoch"
    if atr_pct <= 1.2 and rsi_value < 70:
        return "niedrig"
    return "mittel"


def _strength_label(score):
    if score >= 45:
        return "hoch"
    if score >= 30:
        return "mittel"
    return "niedrig"


def _build_reason_list(last, relative_strength_pct, fundamental_score):
    reasons = []

    if bool(last.get("trend_ok", False)):
        reasons.append("über SMA200")
    if bool(last.get("breakout_ok", False)):
        reasons.append("Breakout")
    if bool(last.get("momentum_ok", False)):
        reasons.append("EMA/RSI positiv")
    if bool(last.get("volatility_ok", False)):
        reasons.append("ausreichende Volatilität")
    if relative_strength_pct is not None and relative_strength_pct >= MIN_RELATIVE_STRENGTH_PCT:
        reasons.append("stärker als Benchmark")
    if fundamental_score >= 2:
        reasons.append("einfach fundamental solide")

    return reasons


def _future_recommendation(score, current_signal, trend_ok, volatility_ok, relative_strength_ok):
    if current_signal == "BUY" and trend_ok and volatility_ok and relative_strength_ok and score >= MIN_SCORE_FOR_BUY:
        return "BUY"
    if trend_ok and score >= MIN_SCORE_FOR_WATCH:
        return "WATCH"
    if current_signal == "SELL":
        return "SELL"
    return "HOLD"


def _calc_return_pct(close_series, lookback):
    if close_series is None or len(close_series) <= lookback:
        return None

    current = float(close_series.iloc[-1])
    past = float(close_series.iloc[-1 - lookback])

    if past == 0:
        return None

    return ((current / past) - 1) * 100


def _calc_relative_strength_pct(df, benchmark_df):
    if benchmark_df is None or benchmark_df.empty:
        return None

    stock_ret = _calc_return_pct(df["Close"], RELATIVE_STRENGTH_LOOKBACK)
    bench_ret = _calc_return_pct(benchmark_df["Close"], RELATIVE_STRENGTH_LOOKBACK)

    if stock_ret is None or bench_ret is None:
        return None

    return stock_ret - bench_ret


def _calc_fundamental_score(fundamentals):
    if not fundamentals:
        return 0

    score = 0

    earnings_growth = fundamentals.get("earnings_growth")
    revenue_growth = fundamentals.get("revenue_growth")
    profit_margins = fundamentals.get("profit_margins")
    return_on_equity = fundamentals.get("return_on_equity")
    trailing_pe = fundamentals.get("trailing_pe")
    forward_pe = fundamentals.get("forward_pe")

    if earnings_growth is not None and earnings_growth > 0:
        score += 1
    if revenue_growth is not None and revenue_growth > 0:
        score += 1
    if profit_margins is not None and profit_margins > 0:
        score += 1
    if return_on_equity is not None and return_on_equity > 0.10:
        score += 1
    if trailing_pe is not None and 0 < trailing_pe < 35:
        score += 1
    if forward_pe is not None and 0 < forward_pe < 30:
        score += 1

    return score


def analyze_symbol(df, symbol, benchmark_df=None, fundamentals=None):
    min_len = max(TREND_SMA, BREAKOUT_LOOKBACK, RELATIVE_STRENGTH_LOOKBACK + 1, 30)

    if df is None or df.empty or len(df) < min_len:
        return None

    df = add_signals(df)
    last = df.iloc[-1]

    if pd.isna(last["atr_pct"]) or pd.isna(last["rsi"]) or pd.isna(last["sma_trend"]):
        return None

    lookback = min(20, len(df) - 1)
    momentum = ((last["Close"] / df["Close"].iloc[-1 - lookback]) - 1) * 100 if lookback > 0 else 0.0
    volatility = float(last["atr_pct"])
    avg_volume = float(df["Volume"].tail(20).mean())
    current_signal = normalize_signal_from_row(last)

    relative_strength_pct = _calc_relative_strength_pct(df, benchmark_df)
    relative_strength_ok = (
        relative_strength_pct is not None and relative_strength_pct >= MIN_RELATIVE_STRENGTH_PCT
    )

    fundamental_score = _calc_fundamental_score(fundamentals or {})

    score = (
        momentum * 0.35
        + volatility * 12
        + (10 if bool(last["trend_ok"]) else 0)
        + (8 if bool(last["breakout_ok"]) else 0)
        + (5 if bool(last["momentum_ok"]) else 0)
        + (8 if relative_strength_ok else 0)
        + (fundamental_score * 2.5)
    )

    reasons = _build_reason_list(last, relative_strength_pct, fundamental_score)
    risk = _risk_level(float(last["atr_pct"]), float(last["rsi"]))
    strength = _strength_label(score)
    future_signal = _future_recommendation(
        score=score,
        current_signal=current_signal,
        trend_ok=bool(last["trend_ok"]),
        volatility_ok=bool(last["volatility_ok"]),
        relative_strength_ok=relative_strength_ok,
    )

    is_candidate = bool(last["trend_ok"]) and bool(last["volatility_ok"])

    return {
        "symbol": symbol,
        "momentum": momentum,
        "volatility": volatility,
        "avg_volume": avg_volume,
        "score": score,
        "is_candidate": is_candidate,
        "current_signal": current_signal,
        "future_signal": future_signal,
        "strength": strength,
        "risk": risk,
        "reasons": reasons,
        "trend_ok": bool(last["trend_ok"]),
        "breakout_ok": bool(last["breakout_ok"]),
        "momentum_ok": bool(last["momentum_ok"]),
        "volatility_ok": bool(last["volatility_ok"]),
        "relative_strength_pct": relative_strength_pct,
        "relative_strength_ok": relative_strength_ok,
        "fundamental_score": fundamental_score,
    }
