from dataclasses import dataclass, field
from config import FEE_PER_TRADE, SLIPPAGE_PCT


@dataclass
class Broker:
    cash: float
    position: int = 0
    avg_entry: float = 0.0
    trades: list = field(default_factory=list)
    closed_trades: list = field(default_factory=list)
    open_trade: dict | None = None

    def buy(self, price, qty, ts):
        fill = price * (1 + SLIPPAGE_PCT)
        cost = fill * qty + FEE_PER_TRADE

        if cost > self.cash or qty <= 0:
            return False

        self.cash -= cost
        self.position += qty
        self.avg_entry = fill

        self.open_trade = {
            "buy_time": ts,
            "buy_price": fill,
            "qty": qty,
            "buy_total": cost,
        }

        return True

    def sell(self, price, ts):
        if self.position == 0:
            return False

        fill = price * (1 - SLIPPAGE_PCT)
        total = fill * self.position - FEE_PER_TRADE

        pnl = total - self.open_trade["buy_total"]
        pnl_pct = pnl / self.open_trade["buy_total"] * 100

        self.closed_trades.append({
            **self.open_trade,
            "sell_time": ts,
            "sell_price": fill,
            "sell_total": total,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })

        self.cash += total
        self.position = 0
        self.open_trade = None

        return True

    def summary(self, price):
        return {
            "cash": self.cash,
            "position": self.position,
            "equity": self.cash + self.position * price,
            "closed_trades": self.closed_trades,
        }
