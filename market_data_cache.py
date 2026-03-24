from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import re
import time

import pandas as pd

from data_loader import load_data, load_fx_to_eur_data


CACHE_DIR = Path(".cache/market_data")
DEFAULT_MAX_WORKERS = 8


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_part(value):
    text = str(value or "")
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    return text.strip("_") or "x"


def _cache_path(prefix, key_parts):
    _ensure_cache_dir()
    name = "__".join([_safe_part(prefix)] + [_safe_part(p) for p in key_parts]) + ".pkl"
    return CACHE_DIR / name


def _is_fresh(path, ttl_seconds):
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age <= ttl_seconds


def _load_pickle(path):
    try:
        return pd.read_pickle(path)
    except Exception:
        return None


def _save_pickle(path, df):
    try:
        df.to_pickle(path)
    except Exception:
        pass


def _normalize_df(df):
    if df is None:
        return None
    if isinstance(df, pd.DataFrame):
        return df
    try:
        return pd.DataFrame(df)
    except Exception:
        return None


def load_data_cached(symbol, period, interval, ttl_seconds=900):
    path = _cache_path("symbol", [symbol, period, interval])

    if _is_fresh(path, ttl_seconds):
        cached = _load_pickle(path)
        if cached is not None:
            return cached

    df = _normalize_df(load_data(symbol, period, interval))
    if df is not None and not df.empty:
        _save_pickle(path, df)
    return df


def load_benchmark_cached(symbol, period, interval, ttl_seconds=900):
    path = _cache_path("benchmark", [symbol, period, interval])

    if _is_fresh(path, ttl_seconds):
        cached = _load_pickle(path)
        if cached is not None:
            return cached

    df = _normalize_df(load_data(symbol, period, interval))
    if df is not None and not df.empty:
        _save_pickle(path, df)
    return df


def load_fx_to_eur_data_cached(currency, period, interval, ttl_seconds=3600):
    path = _cache_path("fx", [currency, period, interval])

    if _is_fresh(path, ttl_seconds):
        cached = _load_pickle(path)
        if cached is not None:
            return cached

    df = _normalize_df(load_fx_to_eur_data(currency, period, interval))
    if df is not None and not df.empty:
        _save_pickle(path, df)
    return df


def load_data_batch_cached(
    symbols,
    period,
    interval,
    ttl_seconds=900,
    max_workers=DEFAULT_MAX_WORKERS,
):
    symbols = [str(s).strip().upper() for s in symbols if str(s).strip()]
    results = {}
    missing = []

    for symbol in symbols:
        path = _cache_path("symbol", [symbol, period, interval])

        if _is_fresh(path, ttl_seconds):
            cached = _load_pickle(path)
            if cached is not None:
                results[symbol] = cached
                continue

        missing.append(symbol)

    if not missing:
        return results

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(load_data, symbol, period, interval): symbol
            for symbol in missing
        }

        for future in as_completed(future_map):
            symbol = future_map[future]
            try:
                df = _normalize_df(future.result())
            except Exception:
                df = None

            if df is None:
                continue

            results[symbol] = df
            if not df.empty:
                path = _cache_path("symbol", [symbol, period, interval])
                _save_pickle(path, df)

    return results
