import yfinance as yf
import pandas as pd


def load_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)

    if df is None or df.empty:
        return pd.DataFrame()

    if hasattr(df.columns, "levels"):
        df.columns = [c[0] for c in df.columns]

    return df[["Open", "High", "Low", "Close", "Volume"]]
