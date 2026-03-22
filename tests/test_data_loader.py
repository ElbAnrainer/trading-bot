import pandas as pd

from data_loader import (
    _normalize_symbol,
    _postprocess_download_df,
    fx_rate_to_eur_at,
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
