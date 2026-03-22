def check_signal(df):
    if df is None or df.empty or len(df) < 6:
        return None

    last_close = df["Close"].iloc[-1]
    prev_high = df["High"].iloc[-6:-1].max()

    if float(last_close) > float(prev_high):
        return "BUY"

    return None
