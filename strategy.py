import pandas as pd
from config import ALLOC_PCT


def add_signals(df):
    df = df.copy()

    df["sma_fast"] = df["Close"].rolling(5).mean()
    df["sma_slow"] = df["Close"].rolling(20).mean()

    df["signal"] = 0
    df.loc[df["sma_fast"] > df["sma_slow"], "signal"] = 1
    df.loc[df["sma_fast"] < df["sma_slow"], "signal"] = -1

    return df


def normalize_signal(s):
    return "BUY" if s == 1 else "SELL" if s == -1 else "HOLD"


def compute_qty(cash, price):
    return int((cash * ALLOC_PCT) // price)


def analyze_symbol(df, symbol):
    if df.empty or len(df) < 20:
        return None

    last = df["Close"].iloc[-1]
    past = df["Close"].iloc[-20]

    momentum = (last / past - 1) * 100
    avg_volume = df["Volume"].tail(20).mean()
    volatility = df["Close"].pct_change().std() * 100

    score = momentum + volatility

    return {
        "symbol": symbol,
        "momentum": momentum,
        "volatility": volatility,
        "avg_volume": avg_volume,
        "score": score,
        "is_candidate": True
    }
