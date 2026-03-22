from dataclasses import dataclass, field

from config import BROKER_FEE_NATIVE, FX_FEE_PCT, SLIPPAGE_PCT


@dataclass
class Broker:
    cash_eur: float
    position: int = 0
    avg_entry_native: float = 0.0
    asset_currency: str = "USD"
    trades: list = field(default_factory=list)
    closed_trades: list = field(default_factory=list)
    open_trade: dict | None = None

    def buy(self, price_native, qty, ts, fx_rate_to_eur, asset_currency):
        fill_native = price_native * (1 + SLIPPAGE_PCT)
        gross_native = fill_native * qty
        total_native = gross_native + BROKER_FEE_NATIVE
        total_eur = total_native * fx_rate_to_eur * (1 + FX_FEE_PCT)

        if total_eur > self.cash_eur or qty <= 0:
            return False

        self.cash_eur -= total_eur
        self.position += qty
        self.avg_entry_native = fill_native
        self.asset_currency = asset_currency

        self.open_trade = {
            "buy_time": ts,
            "buy_price_native": fill_native,
            "buy_total_native": total_native,
            "buy_total_eur": total_eur,
            "buy_fx_rate": fx_rate_to_eur,
            "qty": qty,
            "native_currency": asset_currency,
        }

        self.trades.append(
            {
                "side": "BUY",
                "time": ts,
                "price_native": fill_native,
                "qty": qty,
                "total_native": total_native,
                "total_eur": total_eur,
                "native_currency": asset_currency,
            }
        )

        return True

    def sell(self, price_native, ts, fx_rate_to_eur, reason="SIGNAL"):
        if self.position == 0 or self.open_trade is None:
            return False

        qty = self.position
        fill_native = price_native * (1 - SLIPPAGE_PCT)
        gross_native = fill_native * qty
        total_native = gross_native - BROKER_FEE_NATIVE
        total_eur = total_native * fx_rate_to_eur * (1 - FX_FEE_PCT)

        pnl_native = total_native - self.open_trade["buy_total_native"]
        pnl_eur = total_eur - self.open_trade["buy_total_eur"]
        pnl_pct_eur = (
            pnl_eur / self.open_trade["buy_total_eur"] * 100
            if self.open_trade["buy_total_eur"] else 0.0
        )

        closed = {
            **self.open_trade,
            "sell_time": ts,
            "sell_price_native": fill_native,
            "sell_total_native": total_native,
            "sell_total_eur": total_eur,
            "sell_fx_rate": fx_rate_to_eur,
            "pnl_native": pnl_native,
            "pnl_eur": pnl_eur,
            "pnl_pct_eur": pnl_pct_eur,
            "reason": reason,
        }

        self.closed_trades.append(closed)
        self.trades.append(
            {
                "side": "SELL",
                "time": ts,
                "price_native": fill_native,
                "qty": qty,
                "total_native": total_native,
                "total_eur": total_eur,
                "native_currency": self.asset_currency,
                "reason": reason,
            }
        )

        self.cash_eur += total_eur
        self.position = 0
        self.avg_entry_native = 0.0
        self.open_trade = None

        return True

    def summary(self, price_native, fx_rate_to_eur):
        position_value_native = self.position * price_native
        position_value_eur = position_value_native * fx_rate_to_eur
        equity_eur = self.cash_eur + position_value_eur

        return {
            "cash_eur": self.cash_eur,
            "position": self.position,
            "position_value_native": position_value_native,
            "position_value_eur": position_value_eur,
            "equity_eur": equity_eur,
            "closed_trades": self.closed_trades,
            "native_currency": self.asset_currency,
        }
