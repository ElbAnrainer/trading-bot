import math
import time
from dataclasses import dataclass
from datetime import datetime, time as dtime, timezone
from zoneinfo import ZoneInfo

from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.wrapper import EWrapper


TZ = ZoneInfo("Europe/Berlin")
NY = ZoneInfo("America/New_York")


@dataclass
class BotConfig:
    symbol: str = "AAPL"
    exchange: str = "SMART"
    currency: str = "USD"
    sec_type: str = "STK"
    host: str = "127.0.0.1"
    port: int = 7497  # 7497 paper TWS, 7496 live TWS; Gateway often 4002/4001
    client_id: int = 7
    risk_per_trade_eur: float = 50.0
    stop_loss_pct: float = 0.005  # 0.5%
    take_profit_rr: float = 1.5
    breakout_lookback_bars: int = 6  # prior 30 min on 5m bars
    bar_size: str = "5 mins"
    duration: str = "2 D"
    trade_window_start: dtime = dtime(15, 35)  # CET/CEST rough NY open + buffer
    trade_window_end: dtime = dtime(20, 30)
    flatten_time: dtime = dtime(21, 45)
    max_shares: int = 50
    paper: bool = True


class IBKRDayTradingBot(EWrapper, EClient):
    def __init__(self, config: BotConfig):
        EClient.__init__(self, self)
        self.cfg = config
        self.next_order_id = None
        self.req_id = 1
        self.historical = []
        self.last_price = None
        self.position_size = 0
        self.avg_cost = 0.0
        self.pending_order = False
        self.last_signal_ts = None

    # ---------- IB callbacks ----------
    def nextValidId(self, orderId: int):
        self.next_order_id = orderId
        print(f"Connected. Next order id: {orderId}")
        self.req_positions()

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        print(f"IB error reqId={reqId} code={errorCode} msg={errorString}")

    def position(self, account, contract, position, avgCost):
        if contract.symbol == self.cfg.symbol and contract.secType == self.cfg.sec_type:
            self.position_size = int(position)
            self.avg_cost = float(avgCost)

    def positionEnd(self):
        print(f"Position sync done. Shares={self.position_size}, avg={self.avg_cost}")

    def historicalData(self, reqId, bar):
        self.historical.append({
            "time": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        })

    def historicalDataEnd(self, reqId, start, end):
        print(f"Historical data complete: {len(self.historical)} bars")
        self.evaluate_and_trade()

    def tickPrice(self, reqId, tickType, price, attrib):
        if price > 0:
            self.last_price = price

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, *args):
        print(f"Order {orderId}: {status}, filled={filled}, remaining={remaining}, avg={avgFillPrice}")
        if status in {"Filled", "Cancelled", "Inactive"}:
            self.pending_order = False

    # ---------- utility ----------
    def stock_contract(self) -> Contract:
        c = Contract()
        c.symbol = self.cfg.symbol
        c.secType = self.cfg.sec_type
        c.exchange = self.cfg.exchange
        c.currency = self.cfg.currency
        return c

    def market_order(self, action: str, quantity: int) -> Order:
        o = Order()
        o.action = action
        o.orderType = "MKT"
        o.totalQuantity = quantity
        o.tif = "DAY"
        return o

    def stop_order(self, action: str, quantity: int, stop_price: float) -> Order:
        o = Order()
        o.action = action
        o.orderType = "STP"
        o.auxPrice = round(stop_price, 2)
        o.totalQuantity = quantity
        o.tif = "DAY"
        return o

    def limit_order(self, action: str, quantity: int, limit_price: float) -> Order:
        o = Order()
        o.action = action
        o.orderType = "LMT"
        o.lmtPrice = round(limit_price, 2)
        o.totalQuantity = quantity
        o.tif = "DAY"
        return o

    def now_berlin(self) -> datetime:
        return datetime.now(timezone.utc).astimezone(TZ)

    def in_trade_window(self) -> bool:
        t = self.now_berlin().timetz().replace(tzinfo=None)
        return self.cfg.trade_window_start <= t <= self.cfg.trade_window_end

    def should_flatten(self) -> bool:
        t = self.now_berlin().timetz().replace(tzinfo=None)
        return t >= self.cfg.flatten_time

    def calc_position_size(self, entry: float, stop: float) -> int:
        risk_per_share = abs(entry - stop)
        if risk_per_share <= 0:
            return 0
        shares = math.floor(self.cfg.risk_per_trade_eur / risk_per_share)
        return max(0, min(shares, self.cfg.max_shares))

    # ---------- requests ----------
    def req_positions(self):
        self.reqPositions()

    def req_market_data(self):
        contract = self.stock_contract()
        self.reqMarketDataType(3)  # delayed if live unavailable
        self.reqMktData(self.req_id, contract, "", False, False, [])
        self.req_id += 1

    def req_bars(self):
        self.historical = []
        contract = self.stock_contract()
        self.reqHistoricalData(
            self.req_id,
            contract,
            "",
            self.cfg.duration,
            self.cfg.bar_size,
            "TRADES",
            1,
            1,
            False,
            [],
        )
        self.req_id += 1

    # ---------- strategy ----------
    def evaluate_and_trade(self):
        if not self.in_trade_window():
            print("Outside trade window; no new entries.")
            return
        if self.pending_order:
            print("Pending order exists; skipping.")
            return
        if len(self.historical) < self.cfg.breakout_lookback_bars + 2:
            print("Not enough bars.")
            return

        bars = self.historical[:-1]  # ignore potentially incomplete latest bar
        recent = bars[-(self.cfg.breakout_lookback_bars + 1):]
        previous_bars = recent[:-1]
        signal_bar = recent[-1]

        breakout_high = max(b["high"] for b in previous_bars)
        vwap_proxy = sum(b["close"] * b["volume"] for b in previous_bars if b["volume"] is not None) / max(
            1, sum(b["volume"] for b in previous_bars if b["volume"] is not None)
        )

        close_price = signal_bar["close"]
        if self.position_size == 0:
            if close_price > breakout_high and close_price > vwap_proxy:
                entry = close_price
                stop = entry * (1 - self.cfg.stop_loss_pct)
                take_profit = entry + ((entry - stop) * self.cfg.take_profit_rr)
                qty = self.calc_position_size(entry, stop)
                if qty <= 0:
                    print("Calculated quantity is zero; skipping.")
                    return
                self.place_bracket_buy(qty, entry, stop, take_profit)
            else:
                print(f"No entry. close={close_price:.2f}, breakout={breakout_high:.2f}, vwap_proxy={vwap_proxy:.2f}")
        else:
            print(f"Already in position: {self.position_size} shares")

    def place_bracket_buy(self, qty: int, entry: float, stop: float, take_profit: float):
        base_id = self.next_order_id
        parent = self.market_order("BUY", qty)
        parent.orderId = base_id
        parent.transmit = False

        tp = self.limit_order("SELL", qty, take_profit)
        tp.orderId = base_id + 1
        tp.parentId = base_id
        tp.transmit = False

        sl = self.stop_order("SELL", qty, stop)
        sl.orderId = base_id + 2
        sl.parentId = base_id
        sl.transmit = True

        contract = self.stock_contract()
        self.placeOrder(parent.orderId, contract, parent)
        self.placeOrder(tp.orderId, contract, tp)
        self.placeOrder(sl.orderId, contract, sl)
        self.next_order_id += 3
        self.pending_order = True
        print(
            f"Bracket BUY sent: qty={qty}, entry≈{entry:.2f}, stop={stop:.2f}, take_profit={take_profit:.2f}"
        )

    def flatten_position(self):
        if self.position_size <= 0 or self.pending_order:
            return
        contract = self.stock_contract()
        order = self.market_order("SELL", self.position_size)
        order.orderId = self.next_order_id
        self.placeOrder(order.orderId, contract, order)
        self.next_order_id += 1
        self.pending_order = True
        print(f"Flattened {self.position_size} shares at market")

    # ---------- loop ----------
    def run_cycle(self):
        self.req_market_data()
        self.req_bars()
        if self.should_flatten():
            self.flatten_position()


def main():
    cfg = BotConfig()
    app = IBKRDayTradingBot(cfg)
    app.connect(cfg.host, cfg.port, clientId=cfg.client_id)

    import threading
    threading.Thread(target=app.run, daemon=True).start()

    time.sleep(3)
    while True:
        try:
            app.run_cycle()
            time.sleep(60)
        except KeyboardInterrupt:
            print("Stopping bot...")
            break
        except Exception as exc:
            print(f"Loop error: {exc}")
            time.sleep(5)

    app.disconnect()


if __name__ == "__main__":
   
