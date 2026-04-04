import pandas as pd

import data_loader

from data_loader import (
    _backoff_delay_seconds,
    _normalize_symbol,
    _postprocess_download_df,
    fx_rate_to_eur_at,
    load_data,
    load_ticker_metadata,
    latest_rate_to_eur,
    fallback_rate_to_eur,
)


def test_normalize_symbol_converts_dot_to_dash():
    assert _normalize_symbol("BRK.B") == "BRK-B"
    assert _normalize_symbol("AAPL") == "AAPL"


def test_postprocess_download_df_keeps_required_columns():
    df = pd.DataFrame(
        {
            "Open": [1, 2],
            "High": [2, 3],
            "Low": [0.5, 1.5],
            "Close": [1.5, 2.5],
            "Volume": [1000, 2000],
        }
    )

    out = _postprocess_download_df(df)

    assert list(out.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(out) == 2


def test_latest_rate_to_eur():
    fx_df = pd.DataFrame(
        {"fx_to_eur": [0.90, 0.95]},
        index=pd.to_datetime(["2026-03-20", "2026-03-21"]),
    )

    rate = latest_rate_to_eur(fx_df, 0.92)
    assert rate == 0.95


def test_fx_rate_to_eur_at():
    fx_df = pd.DataFrame(
        {"fx_to_eur": [0.90, 0.95]},
        index=pd.to_datetime(["2026-03-20", "2026-03-21"]),
    )

    rate = fx_rate_to_eur_at("2026-03-20 12:00:00", fx_df, 0.92)
    assert rate == 0.90


def test_fallback_rate_to_eur_known_currency():
    rate = fallback_rate_to_eur("USD")
    assert rate > 0


def test_fallback_rate_to_eur_unknown_currency_defaults_to_one():
    rate = fallback_rate_to_eur("XYZ")
    assert rate == 1.0


def test_backoff_delay_seconds_grows_exponentially():
    assert _backoff_delay_seconds(1.0, 0) == 1.0
    assert _backoff_delay_seconds(1.0, 1) == 2.0
    assert _backoff_delay_seconds(1.0, 2) == 4.0


def test_load_data_retries_after_429_and_succeeds(monkeypatch):
    calls = []
    sleeps = []
    good_df = pd.DataFrame(
        {
            "Open": [1.0],
            "High": [2.0],
            "Low": [0.5],
            "Close": [1.5],
            "Volume": [1000],
        }
    )

    def fake_download(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RuntimeError("HTTP 429 Too Many Requests")
        return good_df

    monkeypatch.setattr(data_loader.yf, "download", fake_download)
    monkeypatch.setattr(data_loader.time, "sleep", lambda seconds: sleeps.append(seconds))

    out = load_data("AAPL", "1mo", "1d", retries=2, pause_seconds=1.0)

    assert not out.empty
    assert list(out.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(calls) == 2
    assert sleeps == [1.0]


def test_load_ticker_metadata_retries_get_info_and_sets_fetched_at(monkeypatch):
    sleeps = []
    state = {"calls": 0}

    class FakeTicker:
        def get_info(self):
            state["calls"] += 1
            if state["calls"] == 1:
                raise RuntimeError("Too Many Requests")
            return {
                "longName": "Apple Inc.",
                "currency": "USD",
                "wkn": "865985",
            }

    monkeypatch.setattr(data_loader.yf, "Ticker", lambda symbol: FakeTicker())
    monkeypatch.setattr(data_loader.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(
        data_loader,
        "resolve_identifiers",
        lambda **kwargs: {"isin": "US0378331005", "wkn": "865985"},
    )

    meta = load_ticker_metadata("AAPL")

    assert meta["name"] == "Apple Inc."
    assert meta["isin"] == "US0378331005"
    assert meta["wkn"] == "865985"
    assert meta["currency"] == "USD"
    assert meta["fetched_at"]
    assert state["calls"] == 2
    assert sleeps == [1.0]
