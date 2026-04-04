import os
import time

import pandas as pd

import market_data_cache as mdc


def test_load_data_cached_returns_stale_cache_when_refresh_fetch_is_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(mdc, "CACHE_DIR", tmp_path)

    stale_df = pd.DataFrame({"Close": [101.0]})
    cache_path = mdc._cache_path("symbol", ["AAPL", "1mo", "1d"])
    stale_df.to_pickle(cache_path)
    old_ts = time.time() - 3600
    os.utime(cache_path, (old_ts, old_ts))

    monkeypatch.setattr(mdc, "load_data", lambda symbol, period, interval: pd.DataFrame())

    out = mdc.load_data_cached("AAPL", "1mo", "1d", ttl_seconds=60)

    pd.testing.assert_frame_equal(out, stale_df)


def test_load_data_batch_cached_prefers_cached_and_falls_back_to_stale(monkeypatch, tmp_path):
    monkeypatch.setattr(mdc, "CACHE_DIR", tmp_path)

    fresh_df = pd.DataFrame({"Close": [150.0]})
    stale_df = pd.DataFrame({"Close": [90.0]})
    new_df = pd.DataFrame({"Close": [210.0]})

    fresh_path = mdc._cache_path("symbol", ["AAA", "1mo", "1d"])
    stale_path = mdc._cache_path("symbol", ["BBB", "1mo", "1d"])

    fresh_df.to_pickle(fresh_path)
    stale_df.to_pickle(stale_path)

    old_ts = time.time() - 3600
    os.utime(stale_path, (old_ts, old_ts))

    monkeypatch.setattr(
        mdc,
        "load_data_batch",
        lambda symbols, period, interval: {"CCC": new_df},
    )

    out = mdc.load_data_batch_cached(["AAA", "BBB", "CCC"], "1mo", "1d", ttl_seconds=60)

    pd.testing.assert_frame_equal(out["AAA"], fresh_df)
    pd.testing.assert_frame_equal(out["BBB"], stale_df)
    pd.testing.assert_frame_equal(out["CCC"], new_df)
