import math
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


STOP_LOSS_PCT = 0.08
TAKE_PROFIT_PCT = 0.16


def stop_loss_price(entry_price: float) -> float:
    return float(entry_price) * (1.0 - STOP_LOSS_PCT)


def take_profit_price(entry_price: float) -> float:
    return float(entry_price) * (1.0 + TAKE_PROFIT_PCT)


def compute_qty(cash_eur: float, price_eur: float) -> int:
    if price_eur <= 0:
        return 0
    return max(0, int(cash_eur // price_eur))


def _safe_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


def _rolling_breakout(close: pd.Series, lookback: int = 20) -> pd.Series:
    prev_high = close.shift(1).rolling(lookback).max()
    return close > prev_high


def _relative_strength_pct(close: pd.Series, benchmark_close: Optional[pd.Series]) -> float:
    if benchmark_close is None or benchmark_close.empty or close.empty:
        return 0.0

    aligned = pd.concat(
        [
            close.rename("stock"),
            benchmark_close.rename("bench"),
        ],
        axis=1,
        join="inner",
    ).dropna()

    if len(aligned) < 20:
        return 0.0

    stock_return = (aligned["stock"].iloc[-1] / aligned["stock"].iloc[0] - 1.0) * 100.0
    bench_return = (aligned["bench"].iloc[-1] / aligned["bench"].iloc[0] - 1.0) * 100.0
    return float(stock_return - bench_return)


def _fundamental_score(fundamentals: Optional[Dict]) -> int:
    if not fundamentals:
        return 0

    score = 0

    pe = fundamentals.get("trailingPE")
    if pe is not None and pe > 0 and pe < 35:
        score += 1

    revenue_growth = fundamentals.get("revenueGrowth")
    if revenue_growth is not None and revenue_growth > 0:
        score += 1

    earnings_growth = fundamentals.get("earningsGrowth")
    if earnings_growth is not None and earnings_growth > 0:
        score += 1

    profit_margin = fundamentals.get("profitMargins")
    if profit_margin is not None and profit_margin > 0:
        score += 1

    debt_to_equity = fundamentals.get("debtToEquity")
    if debt_to_equity is not None and debt_to_equity >= 0 and debt_to_equity < 150:
        score += 1

    return score


def _strength_label(score: float) -> str:
    if score >= 70:
        return "hoch"
    if score >= 45:
        return "mittel"
    return "niedrig"


def _risk_label(volatility_pct: float, relative_strength_pct: float) -> str:
    if volatility_pct >= 4.5:
        return "hoch"
    if volatility_pct >= 2.5:
        return "mittel"
    if relative_strength_pct < -5:
        return "mittel"
    return "niedrig"


def add_signals(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=list(df.columns) if df is not None else [])

    out = df.copy()

    close = _safe_series(out, "Close")
    high = _safe_series(out, "High")
    low = _safe_series(out, "Low")
    volume = _safe_series(out, "Volume")

    # ------------------------------------------------------------
    # Kompatibilitäts-Spalten für Tests / bestehende Verträge
    # ------------------------------------------------------------
    out["ema_fast"] = close.ewm(span=12, adjust=False).mean()
    out["ema_slow"] = close.ewm(span=26, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean().replace(0, np.nan)
    rs = avg_gain / avg_loss
    out["rsi"] = 100 - (100 / (1 + rs))
    out["rsi"] = out["rsi"].fillna(50.0)

    out["sma_trend"] = close.rolling(50).mean()

    prev_close = close.shift(1)
    tr_components = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    )
    true_range = tr_components.max(axis=1)
    out["atr"] = true_range.rolling(14).mean()
    out["atr_pct"] = np.where(close > 0, (out["atr"] / close) * 100.0, 0.0)

    out["breakout_high"] = close.shift(1).rolling(20).max()
    out["breakout_low"] = close.shift(1).rolling(20).min()

    # ------------------------------------------------------------
    # Erweiterte interne Spalten
    # ------------------------------------------------------------
    out["sma20"] = close.rolling(20).mean()
    out["sma50"] = close.rolling(50).mean()
    out["sma200"] = close.rolling(200).mean()
    out["volume_sma20"] = volume.rolling(20).mean()

    out["momentum_20"] = close.pct_change(20)
    out["momentum_60"] = close.pct_change(60)

    out["return_1d"] = close.pct_change()
    out["volatility_20"] = out["return_1d"].rolling(20).std() * 100.0

    out["breakout_20"] = _rolling_breakout(close, 20)

    # ------------------------------------------------------------
    # Logik-Spalten, die auch der Test erwartet
    # ------------------------------------------------------------
    out["trend_ok"] = (close > out["sma50"]) & (out["ema_fast"] >= out["ema_slow"])
    out["volatility_ok"] = out["atr_pct"] <= 6.0
    out["momentum_ok"] = (out["momentum_20"] > 0.01) | (out["rsi"] > 52)
    out["breakout_ok"] = close > out["breakout_high"]

    volume_ok = volume >= (out["volume_sma20"] * 0.8)

    # Buy-freundlicher, aber weiterhin nachvollziehbar
    out["buy_signal"] = (
        out["trend_ok"]
        & out["momentum_ok"]
        & out["volatility_ok"]
        & (out["breakout_ok"] | volume_ok)
    )

    out["sell_signal"] = (
        (close < out["sma50"])
        | (out["ema_fast"] < out["ema_slow"])
        | (out["momentum_20"] < -0.03)
        | (out["rsi"] < 45)
    )

    return out


def normalize_signal_from_row(row: pd.Series) -> str:
    if bool(row.get("buy_signal", False)):
        return "BUY"
    if bool(row.get("sell_signal", False)):
        return "SELL"

    close = float(row.get("Close", 0.0))
    sma50 = float(row.get("sma50", row.get("sma_trend", 0.0)))
    sma20 = float(row.get("sma20", 0.0))
    momentum_20 = float(row.get("momentum_20", 0.0))

    if close > sma50 and sma20 >= sma50 and momentum_20 >= 0:
        return "WATCH"

    return "HOLD"


def analyze_symbol(
    df: pd.DataFrame,
    symbol: str,
    benchmark_df: Optional[pd.DataFrame] = None,
    fundamentals: Optional[Dict] = None,
) -> Optional[Dict]:
    if df is None or df.empty:
        return None

    work = add_signals(df).dropna(subset=["Close"])
    if work.empty:
        return None

    close = _safe_series(work, "Close")
    volume = _safe_series(work, "Volume")

    latest = work.iloc[-1]

    latest_close = float(latest["Close"])
    sma20 = float(latest.get("sma20", np.nan))
    sma50 = float(latest.get("sma50", np.nan))
    sma200 = float(latest.get("sma200", np.nan))
    momentum_20 = float(latest.get("momentum_20", 0.0))
    momentum_60 = float(latest.get("momentum_60", 0.0))
    volatility_pct = float(latest.get("volatility_20", 0.0))

    benchmark_close = None
    if benchmark_df is not None and not benchmark_df.empty and "Close" in benchmark_df.columns:
        benchmark_close = pd.to_numeric(benchmark_df["Close"], errors="coerce")

    rs_pct = _relative_strength_pct(close, benchmark_close)
    f_score = _fundamental_score(fundamentals)

    trend_ok = bool(latest.get("trend_ok", False))
    long_trend_ok = bool(not math.isnan(sma200) and latest_close >= sma200)
    breakout_ok = bool(latest.get("breakout_ok", False))
    momentum_ok = bool(latest.get("momentum_ok", False) or momentum_60 > 0.03)
    volatility_ok = bool(latest.get("volatility_ok", False))
    relative_strength_ok = bool(rs_pct >= -2.0)

    reasons: List[str] = []

    if trend_ok:
        reasons.append("über SMA50")
    if long_trend_ok:
        reasons.append("über SMA200")
    if breakout_ok:
        reasons.append("Breakout")
    if momentum_ok:
        reasons.append("Momentum positiv")
    if relative_strength_ok and rs_pct > 0:
        reasons.append("stärker als Markt")
    if f_score >= 2:
        reasons.append("Fundamentaldaten ok")

    score = 0.0
    if trend_ok:
        score += 22
    if long_trend_ok:
        score += 14
    if breakout_ok:
        score += 18
    if momentum_ok:
        score += 16
    if volatility_ok:
        score += 8
    if relative_strength_ok:
        score += 12
    score += min(f_score * 3.0, 15.0)

    score += max(min(rs_pct * 0.6, 8.0), -8.0)
    score += max(min(momentum_20 * 100.0 * 0.3, 6.0), -6.0)

    score = float(max(0.0, min(score, 100.0)))

    current_signal = normalize_signal_from_row(latest)

    if trend_ok and momentum_ok and relative_strength_ok and score >= 50:
        future_signal = "BUY"
    elif trend_ok and score >= 40:
        future_signal = "WATCH"
    elif latest_close < sma50 or momentum_20 < -0.03:
        future_signal = "SELL"
    else:
        future_signal = "HOLD"

    is_candidate = future_signal in ("BUY", "WATCH")

    return {
        "symbol": symbol,
        "avg_volume": float(volume.tail(20).mean()) if not volume.empty else 0.0,
        "trend_ok": trend_ok,
        "long_trend_ok": long_trend_ok,
        "breakout_ok": breakout_ok,
        "momentum_ok": momentum_ok,
        "volatility_ok": volatility_ok,
        "relative_strength_ok": relative_strength_ok,
        "relative_strength_pct": rs_pct,
        "fundamental_score": f_score,
        "score": score,
        "current_signal": current_signal,
        "future_signal": future_signal,
        "strength": _strength_label(score),
        "risk": _risk_label(volatility_pct, rs_pct),
        "reasons": reasons,
        "is_candidate": is_candidate,
        "volatility_pct": volatility_pct,
    }
