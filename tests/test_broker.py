from broker import Broker


def test_buy_reduces_cash_and_increases_position():
    broker = Broker(cash=10000.0)

    ok = broker.buy(price=250.0, qty=4, ts="2026-03-20T19:55:00Z")

    assert ok is True
    assert broker.position == 4
    assert broker.cash < 10000.0
    assert broker.avg_entry > 0
    assert len(broker.trades) == 1
    assert broker.trades[0]["side"] == "BUY"


def test_buy_fails_if_qty_zero():
    broker = Broker(cash=10000.0)

    ok = broker.buy(price=250.0, qty=0, ts="2026-03-20T19:55:00Z")

    assert ok is False
    assert broker.position == 0
    assert broker.cash == 10000.0
    assert broker.trades == []


def test_buy_fails_if_not_enough_cash():
    broker = Broker(cash=100.0)

    ok = broker.buy(price=250.0, qty=4, ts="2026-03-20T19:55:00Z")

    assert ok is False
    assert broker.position == 0
    assert broker.cash == 100.0
    assert broker.trades == []


def test_sell_closes_position_and_increases_cash():
    broker = Broker(cash=10000.0)
    broker.buy(price=250.0, qty=4, ts="2026-03-20T19:55:00Z")

    ok = broker.sell(price=260.0, ts="2026-03-20T20:00:00Z")

    assert ok is True
    assert broker.position == 0
    assert broker.avg_entry == 0
    assert len(broker.trades) == 2
    assert broker.trades[-1]["side"] == "SELL"


def test_sell_fails_if_no_position():
    broker = Broker(cash=10000.0)

    ok = broker.sell(price=260.0, ts="2026-03-20T20:00:00Z")

    assert ok is False
    assert broker.position == 0
    assert broker.cash == 10000.0


def test_summary_contains_expected_keys():
    broker = Broker(cash=10000.0)
    summary = broker.summary(price=250.0)

    assert "cash" in summary
    assert "position" in summary
    assert "avg_entry" in summary
    assert "equity" in summary
