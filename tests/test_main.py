import pandas as pd

import main


def test_choose_interval():
    assert main.choose_interval("1d") == "5m"
    assert main.choose_interval("5d") == "5m"
    assert main.choose_interval("1mo") == "5m"
    assert main.choose_interval("3mo") == "1h"
    assert main.choose_interval("1y") == "1d"
    assert main.choose_interval("3y") == "1d"


def test_get_signal_with_mocked_data(monkeypatch):
    df = pd.DataFrame(
        {
            "Open": list(range(1, 261)),
            "High": [x + 1 for x in range(1, 261)],
            "Low": [x - 1 for x in range(1, 261)],
            "Close": list(range(1, 261)),
            "Volume": [10_000_000] * 260,
        }
    )

    monkeypatch.setattr(main, "load_data", lambda symbol, period, interval: df)

    signal, price_eur, price_native = main.get_signal("AAPL", "1y", "1d", 0.9)

    assert signal in {"BUY", "SELL", "HOLD"}
    assert price_native == 260.0
    assert price_eur == 260.0 * 0.9
