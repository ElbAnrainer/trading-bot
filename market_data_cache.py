from pathlib import Path
import re
import time

import pandas as pd

from config import MARKET_DATA_CACHE_DIR as DEFAULT_MARKET_DATA_CACHE_DIR
from data_loader import load_data, load_data_batch, load_fx_to_eur_data


CACHE_DIR = Path(DEFAULT_MARKET_DATA_CACHE_DIR)
DEFAULT_MAX_WORKERS = 4


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


def _load_cached_pickle(path):
    if not path.exists():
        return None
    return _load_pickle(path)


def load_data_cached(symbol, period, interval, ttl_seconds=900):
    path = _cache_path("symbol", [symbol, period, interval])
    stale = _load_cached_pickle(path)

    if _is_fresh(path, ttl_seconds):
        if stale is not None:
            return stale

    df = _normalize_df(load_data(symbol, period, interval))
    if df is not None and not df.empty:
        _save_pickle(path, df)
        return df
    if stale is not None:
        return stale
    return df


def load_benchmark_cached(symbol, period, interval, ttl_seconds=900):
    path = _cache_path("benchmark", [symbol, period, interval])
    stale = _load_cached_pickle(path)

    if _is_fresh(path, ttl_seconds):
        if stale is not None:
            return stale

    df = _normalize_df(load_data(symbol, period, interval))
    if df is not None and not df.empty:
        _save_pickle(path, df)
        return df
    if stale is not None:
        return stale
    return df


def load_fx_to_eur_data_cached(currency, period, interval, ttl_seconds=3600):
    path = _cache_path("fx", [currency, period, interval])
    stale = _load_cached_pickle(path)

    if _is_fresh(path, ttl_seconds):
        if stale is not None:
            return stale

    df = _normalize_df(load_fx_to_eur_data(currency, period, interval))
    if df is not None and not df.empty:
        _save_pickle(path, df)
        return df
    if stale is not None:
        return stale
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
    stale_by_symbol = {}

    # Kept for API compatibility; batched downloads reduce Yahoo burst traffic
    # more reliably than multiple parallel single-symbol calls.
    _ = max_workers

    for symbol in symbols:
        path = _cache_path("symbol", [symbol, period, interval])
        stale = _load_cached_pickle(path)
        if stale is not None:
            stale_by_symbol[symbol] = stale

        if _is_fresh(path, ttl_seconds):
            if stale is not None:
                results[symbol] = stale
                continue

        missing.append(symbol)

    if not missing:
        return results

    fetched = load_data_batch(missing, period, interval)
    for symbol, df in fetched.items():
        normalized = _normalize_df(df)
        if normalized is None:
            continue
        results[symbol] = normalized
        if not normalized.empty:
            path = _cache_path("symbol", [symbol, period, interval])
            _save_pickle(path, normalized)

    for symbol in missing:
        if symbol in results:
            continue
        stale = stale_by_symbol.get(symbol)
        if stale is not None:
            results[symbol] = stale

    return results
