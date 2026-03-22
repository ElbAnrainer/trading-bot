import pandas as pd
import main


def test_main_buy_flow(monkeypatch):
    df = pd.DataFrame({
        "Open": [1]*25,
        "High": [1]*25,
        "Low": [1]*25,
        "Close": list(range(1, 26)),
        "Volume": [100]*25,
    })

    def fake_load_data(symbol, period, interval):
        return df

    called = {
        "buy": False,
        "sell": False,
        "human": False,
        "technical": False,
    }

    class FakeBroker:
        def __init__(self, cash):
            self.cash = cash
            self.position = 0
            self.avg_entry = 0.0

        def buy(self, price, qty, ts):
            called["buy"] = True
            self.position = qty
            self.avg_entry = price
            self.cash -= price * qty
            return True

        def sell(self, price, ts):
            called["sell"] = True
            return True

        def summary(self, price):
            return {
                "cash": self.cash,
                "position": self.position,
                "avg_entry": self.avg_entry,
                "equity": self.cash + self.position * price,
            }

    def fake_print_human(*args, **kwargs):
        called["human"] = True

    def fake_print_technical(*args, **kwargs):
        called["technical"] = True

    monkeypatch.setattr(main, "load_data", fake_load_data)
    monkeypatch.setattr(main, "Broker", FakeBroker)
    monkeypatch.setattr(main, "print_human", fake_print_human)
    monkeypatch.setattr(main, "print_technical", fake_print_technical)

    main.main()

    assert called["buy"] is True
    assert called["sell"] is False
    assert called["human"] is True
    assert called["technical"] is True
