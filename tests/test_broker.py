from broker import Broker


def test_buy_opens_position():
    broker = Broker(cash_eur=10_000.0)

    ok = broker.buy(
        price_native=100.0,
        qty=5,
        ts="2026-03-22 10:00:00",
        fx_rate_to_eur=0.9,
        asset_currency="USD",
    )

    assert ok is True
    assert broker.position == 5
    assert broker.cash_eur < 10_000.0
    assert broker.open_trade is not None
    assert broker.open_trade["qty"] == 5
    assert broker.open_trade["native_currency"] == "USD"


def test_buy_fails_for_zero_qty():
    broker = Broker(cash_eur=10_000.0)

    ok = broker.buy(
        price_native=100.0,
        qty=0,
        ts="2026-03-22 10:00:00",
        fx_rate_to_eur=0.9,
        asset_currency="USD",
    )

    assert ok is False
    assert broker.position == 0
    assert broker.open_trade is None


def test_sell_closes_position():
    broker = Broker(cash_eur=10_000.0)
    broker.buy(
        price_native=100.0,
        qty=5,
        ts="2026-03-22 10:00:00",
        fx_rate_to_eur=0.9,
        asset_currency="USD",
    )

    ok = broker.sell(
        price_native=110.0,
        ts="2026-03-22 11:00:00",
        fx_rate_to_eur=0.9,
        reason="TAKE_PROFIT",
    )

    assert ok is True
    assert broker.position == 0
    assert broker.open_trade is None
    assert len(broker.closed_trades) == 1
    assert broker.closed_trades[0]["reason"] == "TAKE_PROFIT"
    assert broker.closed_trades[0]["native_currency"] == "USD"


def test_summary_contains_expected_keys():
    broker = Broker(cash_eur=10_000.0)
    summary = broker.summary(price_native=100.0, fx_rate_to_eur=0.9)

    assert "cash_eur" in summary
    assert "position" in summary
    assert "equity_eur" in summary
    assert "closed_trades" in summary
