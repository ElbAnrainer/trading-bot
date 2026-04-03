import time
from io import StringIO
from urllib.request import Request, urlopen

import pandas as pd
import yfinance as yf

from config import FX_FALLBACK_RATES_TO_EUR, FX_SYMBOL, UNIVERSE_SOURCES
from identifier_lookup import resolve_identifiers


SNP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().replace(".", "-")


def _download_html(url: str) -> str:
    req = Request(url, headers=HTTP_HEADERS)
    with urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def _read_html_tables(url: str):
    html = _download_html(url)
    return pd.read_html(StringIO(html))


def fetch_sp500_symbols():
    try:
        tables = _read_html_tables(SNP500_URL)
    except Exception:
        return []

    if not tables:
        return []

    df = tables[0]
    if "Symbol" not in df.columns:
        return []

    return [_normalize_symbol(s) for s in df["Symbol"].dropna().astype(str).tolist()]


def fetch_nasdaq100_symbols():
    try:
        tables = _read_html_tables(NASDAQ100_URL)
    except Exception:
        return []

    for df in tables:
        cols = {str(c).strip().lower(): c for c in df.columns}
        if "ticker" in cols:
            return [_normalize_symbol(s) for s in df[cols["ticker"]].dropna().astype(str).tolist()]
        if "symbol" in cols:
            return [_normalize_symbol(s) for s in df[cols["symbol"]].dropna().astype(str).tolist()]

    return []


def fetch_dynamic_universe():
    universe = set()

    if "sp500" in UNIVERSE_SOURCES:
        universe.update(fetch_sp500_symbols())

    if "nasdaq100" in UNIVERSE_SOURCES:
        universe.update(fetch_nasdaq100_symbols())

    return sorted(universe)


def _flatten_single_symbol_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        level0 = list(df.columns.get_level_values(0))
        level1 = list(df.columns.get_level_values(1))
        needed = ["Open", "High", "Low", "Close", "Volume"]

        if all(col in level0 for col in needed):
            out = pd.DataFrame(index=df.index)
            for col in needed:
                sub = df[col]
                out[col] = sub.iloc[:, 0] if isinstance(sub, pd.DataFrame) else sub
            return out

        if all(col in level1 for col in needed):
            out = pd.DataFrame(index=df.index)
            for col in needed:
                sub = df.xs(col, axis=1, level=1)
                out[col] = sub.iloc[:, 0] if isinstance(sub, pd.DataFrame) else sub
            return out

    return df.copy()


def _postprocess_download_df(df):
    if df is None or df.empty:
        return pd.DataFrame()

    df = _flatten_single_symbol_df(df)

    needed = ["Open", "High", "Low", "Close", "Volume"]
    existing = [c for c in needed if c in df.columns]
    if len(existing) < 5:
        return pd.DataFrame()

    out = df[needed].copy()
    for col in needed:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.dropna(subset=needed)
    return out


def load_data(symbol, period, interval, retries=2, pause_seconds=1.0):
    last_df = pd.DataFrame()

    for attempt in range(retries + 1):
        try:
            df = yf.download(
                symbol,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=False,
                threads=False,
                timeout=20,
            )
            df = _postprocess_download_df(df)
            if not df.empty:
                return df
            last_df = df
        except Exception:
            pass

        if attempt < retries:
            time.sleep(pause_seconds)

    return last_df


def load_data_batch(symbols, period, interval, chunk_size=25, pause_seconds=1.0):
    result = {}

    if not symbols:
        return result

    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i:i + chunk_size]

        try:
            df = yf.download(
                tickers=" ".join(chunk),
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=False,
                threads=False,
                group_by="ticker",
                timeout=30,
            )
        except Exception:
            df = pd.DataFrame()

        if df is None or df.empty:
            time.sleep(pause_seconds)
            continue

        if isinstance(df.columns, pd.MultiIndex):
            for symbol in chunk:
                try:
                    sub = df[symbol].copy()
                    sub = _postprocess_download_df(sub)
                    if not sub.empty:
                        result[symbol] = sub
                except Exception:
                    continue
        else:
            if len(chunk) == 1:
                sub = _postprocess_download_df(df)
                if not sub.empty:
                    result[chunk[0]] = sub

        time.sleep(pause_seconds)

    return result


def _load_single_fx_symbol(fx_symbol, period, interval):
    try:
        df = yf.download(
            fx_symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
            timeout=20,
        )
    except Exception:
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df = _flatten_single_symbol_df(df)

    if "Close" not in df.columns:
        return pd.DataFrame()

    out = df[["Close"]].copy()
    out["Close"] = pd.to_numeric(out["Close"], errors="coerce")
    out = out.dropna(subset=["Close"])
    return out


def load_fx_data(period, interval):
    df = _load_single_fx_symbol(FX_SYMBOL, period, interval)
    if df.empty:
        return pd.DataFrame()

    out = df.rename(columns={"Close": "fx_close"}).copy()
    return out


def load_fx_to_eur_data(currency, period, interval):
    currency = (currency or "USD").upper()

    if currency == "EUR":
        return pd.DataFrame()

    pair1 = f"EUR{currency}=X"
    pair2 = f"{currency}EUR=X"

    df1 = _load_single_fx_symbol(pair1, period, interval)
    if not df1.empty:
        out = df1.rename(columns={"Close": "raw"}).copy()
        out["fx_to_eur"] = 1.0 / out["raw"]
        return out[["fx_to_eur"]]

    df2 = _load_single_fx_symbol(pair2, period, interval)
    if not df2.empty:
        out = df2.rename(columns={"Close": "fx_to_eur"}).copy()
        return out[["fx_to_eur"]]

    return pd.DataFrame()


def _normalize_timestamp(ts, target_index):
    ts = pd.Timestamp(ts)

    if len(target_index) == 0:
        return ts

    idx_tz = target_index.tz
    if idx_tz is not None:
        if ts.tzinfo is None:
            ts = ts.tz_localize(idx_tz)
        else:
            ts = ts.tz_convert(idx_tz)
    else:
        if ts.tzinfo is not None:
            ts = ts.tz_localize(None)

    return ts


def fx_rate_to_eur_at(ts, fx_df, fallback_rate):
    if fx_df is None or fx_df.empty:
        return fallback_rate

    ts = _normalize_timestamp(ts, fx_df.index)

    eligible = fx_df.loc[fx_df.index <= ts]
    if eligible.empty:
        rate = float(fx_df["fx_to_eur"].iloc[0])
    else:
        rate = float(eligible["fx_to_eur"].iloc[-1])

    if rate <= 0:
        return fallback_rate

    return rate


def latest_rate_to_eur(fx_df, fallback_rate):
    if fx_df is None or fx_df.empty:
        return fallback_rate

    rate = float(fx_df["fx_to_eur"].iloc[-1])
    if rate <= 0:
        return fallback_rate

    return rate


def fallback_rate_to_eur(currency):
    return FX_FALLBACK_RATES_TO_EUR.get((currency or "USD").upper(), 1.0)


def load_ticker_metadata(symbol):
    """
    Holt Name / ISIN / Währung / einfache Fundamentaldaten online über yfinance.
    Identifier werden zusätzlich über robuste Web-Fallbacks aufgelöst, weil
    Yahoo/yfinance bei ISIN/WKN inkonsistent sein kann.
    """
    try:
        ticker = yf.Ticker(symbol)
    except Exception:
        return {
            "name": symbol,
            "isin": "-",
            "wkn": "-",
            "currency": "USD",
            "fundamentals": {},
        }

    name = symbol
    isin = "-"
    wkn = "-"
    currency = "USD"
    fundamentals = {}

    try:
        info = ticker.get_info()
    except Exception:
        info = {}

    if isinstance(info, dict):
        name = (
            info.get("longName")
            or info.get("shortName")
            or info.get("displayName")
            or symbol
        )
        wkn = info.get("wkn") or info.get("securityId") or "-"
        currency = info.get("currency") or currency

        fundamentals = {
            "market_cap": info.get("marketCap"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "earnings_growth": info.get("earningsGrowth"),
            "revenue_growth": info.get("revenueGrowth"),
            "profit_margins": info.get("profitMargins"),
            "return_on_equity": info.get("returnOnEquity"),
        }

    identifiers = resolve_identifiers(
        symbol=symbol,
        company_name=name,
        current_isin=isin,
        current_wkn=wkn,
    )

    return {
        "name": name,
        "isin": identifiers["isin"],
        "wkn": identifiers["wkn"],
        "currency": (currency or "USD").upper(),
        "fundamentals": fundamentals,
    }
