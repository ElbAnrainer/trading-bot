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

    def buy(self, price: float, qty: int, ts: str) -> bool:
        fill_price = price * (1 + SLIPPAGE_PCT)
        cost = fill_price * qty + FEE_PER_TRADE

        if cost > self.cash or qty <= 0:
            return False

        if self.position == 0:
            self.avg_entry = fill_price
        else:
            self.avg_entry = (
                (self.avg_entry * self.position) + (fill_price * qty)
            ) / (self.position + qty)

        self.cash -= cost
        self.position += qty

        trade = {
            "side": "BUY",
            "price": fill_price,
            "qty": qty,
            "gross_amount": fill_price * qty,
            "total_cost": cost,
            "time": ts,
        }
        self.trades.append(trade)

        if self.open_trade is None:
            self.open_trade = {
                "buy_time": ts,
                "buy_price": fill_price,
                "qty": qty,
                "buy_gross": fill_price * qty,
                "buy_total": cost,
            }

        return True

    def sell(self, price: float, ts: str) -> bool:
        if self.position == 0:
            return False

        qty = self.position
        fill_price = price * (1 - SLIPPAGE_PCT)
        gross_amount = fill_price * qty
        total_proceeds = gross_amount - FEE_PER_TRADE

        self.cash += total_proceeds

        trade = {
            "side": "SELL",
            "price": fill_price,
            "qty": qty,
            "gross_amount": gross_amount,
            "total_proceeds": total_proceeds,
            "time": ts,
        }
        self.trades.append(trade)

        if self.open_trade is not None:
            pnl = total_proceeds - self.open_trade["buy_total"]
            pnl_pct = 0.0
            if self.open_trade["buy_total"] != 0:
                pnl_pct = (pnl / self.open_trade["buy_total"]) * 100

            closed_trade = {
                "buy_time": self.open_trade["buy_time"],
                "buy_price": self.open_trade["buy_price"],
                "qty": self.open_trade["qty"],
                "buy_gross": self.open_trade["buy_gross"],
                "buy_total": self.open_trade["buy_total"],
                "sell_time": ts,
                "sell_price": fill_price,
                "sell_gross": gross_amount,
                "sell_total": total_proceeds,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
            }
            self.closed_trades.append(closed_trade)
            self.open_trade = None

        self.position = 0
        self.avg_entry = 0.0
        return True

    def summary(self, price: float) -> dict:
        return {
            "cash": self.cash,
            "position": self.position,
            "avg_entry": self.avg_entry,
            "equity": self.cash + self.position * price,
            "closed_trades": self.closed_trades,
        }
