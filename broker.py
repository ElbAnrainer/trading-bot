from dataclasses import dataclass, field
from typing import Optional
from config import FEE_PER_TRADE, SLIPPAGE_PCT


@dataclass
class Broker:
    cash: float
    position: int = 0
    avg_entry: float = 0.0
    trades: list = field(default_factory=list)

    def buy(self, price: float, qty: int, ts: str):
        fill_price = price * (1 + SLIPPAGE_PCT)
        cost = fill_price * qty + FEE_PER_TRADE

        if cost > self.cash or qty <= 0:
            return False

        self.cash -= cost
        self.position += qty
        self.avg_entry = fill_price

        self.trades.append({"side": "BUY", "price": fill_price, "qty": qty})
        return True

    def sell(self, price: float, ts: str):
        if self.position == 0:
            return False

        fill_price = price * (1 - SLIPPAGE_PCT)
        self.cash += fill_price * self.position - FEE_PER_TRADE

        self.trades.append({"side": "SELL", "price": fill_price})
        self.position = 0
        self.avg_entry = 0

        return True

    def summary(self, price):
        return {
            "cash": self.cash,
            "position": self.position,
            "avg_entry": self.avg_entry,
            "equity": self.cash + self.position * price,
        }
