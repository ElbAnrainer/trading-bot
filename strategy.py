import pandas as pd
from config import ALLOC_PCT


def add_signals(df):
    df["sma_fast"] = df["Close"].rolling(5).mean()
    df["sma_slow"] = df["Close"].rolling(20).mean()

    df["signal"] = 0
    df.loc[df["sma_fast"] > df["sma_slow"], "signal"] = 1
    df.loc[df["sma_fast"] < df["sma_slow"], "signal"] = -1

    return df


def normalize_signal(signal):
    return "BUY" if signal == 1 else "SELL" if signal == -1 else "HOLD"


def compute_qty(cash, price):
    budget = cash * ALLOC_PCT
    return int(budget // price)
