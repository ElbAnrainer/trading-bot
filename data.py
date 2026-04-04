import pandas as pd

from market_data_cache import load_data_cached

def get_data(symbol="AAPL"):
    df = load_data_cached(symbol, period="1d", interval="5m", ttl_seconds=300)

    if df.empty:
        return df

    # yfinance liefert teils MultiIndex-Spalten
    if isinstance(df.columns, pd.MultiIndex):
        # Falls Ebene 0 OHLCV ist -> direkt übernehmen
        lvl0 = list(df.columns.get_level_values(0))
        if "Close" in lvl0 and "High" in lvl0:
            df.columns = df.columns.get_level_values(0)
        else:
            # Falls Ebene 1 OHLCV ist
            df.columns = df.columns.get_level_values(1)

    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
