import pandas as pd
import yfinance as yf

def get_data(symbol="AAPL"):
    df = yf.download(
        symbol,
        interval="5m",
        period="1d",
        auto_adjust=False,
        progress=False,
    )

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
