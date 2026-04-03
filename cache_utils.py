import json
import os
from pathlib import Path

from config import CACHE_DIR as DEFAULT_CACHE_DIR, METADATA_CACHE_JSON
CACHE_DIR = Path(DEFAULT_CACHE_DIR)
METADATA_CACHE_FILE = Path(METADATA_CACHE_JSON)


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path):
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_json(path, data):
    _ensure_cache_dir()
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def get_cached_metadata(symbol, loader_func, refresh_predicate=None):
    symbol = str(symbol).strip().upper()
    cache = _load_json(METADATA_CACHE_FILE)

    if symbol in cache:
        cached = cache[symbol]
        if refresh_predicate is None or not refresh_predicate(cached):
            return cached

    meta = loader_func(symbol) or {}
    if not isinstance(meta, dict):
        meta = {}

    cache[symbol] = meta
    _save_json(METADATA_CACHE_FILE, cache)
    return meta


def preload_metadata(symbols, loader_func, refresh_predicate=None):
    cache = _load_json(METADATA_CACHE_FILE)
    updated = False
    result = {}

    for raw_symbol in symbols:
        symbol = str(raw_symbol).strip().upper()
        cached = cache.get(symbol)
        if cached is not None and (refresh_predicate is None or not refresh_predicate(cached)):
            result[symbol] = cached
            continue

        meta = loader_func(symbol) or {}
        if not isinstance(meta, dict):
            meta = {}

        cache[symbol] = meta
        result[symbol] = meta
        updated = True

    if updated:
        _save_json(METADATA_CACHE_FILE, cache)

    return result
