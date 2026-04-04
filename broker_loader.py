import pandas as pd

from market_data_cache import load_data_cached


def load_data(symbol, period, interval):
    df = load_data_cached(symbol, period=period, interval=interval, ttl_seconds=300)

    if df is None or df.empty:
        return pd.DataFrame()

    if hasattr(df.columns, "levels"):
        df.columns = [c[0] for c in df.columns]

    return df[["Open", "High", "Low", "Close", "Volume"]]
