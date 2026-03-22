import yfinance as yf
import pandas as pd


def load_data(symbol: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False,
    )

    if df is None or df.empty:
        return pd.DataFrame()

    if hasattr(df.columns, "levels"):
        df.columns = [c[0] for c in df.columns]

    needed = ["Open", "High", "Low", "Close", "Volume"]
    existing = [col for col in needed if col in df.columns]

    if len(existing) < 5:
        return pd.DataFrame()

    return df[needed].copy()
