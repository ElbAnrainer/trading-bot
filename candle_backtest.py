from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from risk import stop_loss_price, trailing_stop_price
from strategy import add_signals


@dataclass
class Position:
    symbol: str
    entry_price: float
    shares: float
    invested_eur: float
    highest_price: float
    opened_at: str


def _stop_loss_price(entry_price: float, profile_name: str | None = None) -> float:
    return stop_loss_price(entry_price, profile_name=profile_name)


def _trailing_stop_price(highest_price: float, profile_name: str | None = None) -> float:
    return trailing_stop_price(highest_price, profile_name=profile_name)


def latest_signal(df: pd.DataFrame) -> dict[str, Any]:
    """
    Liefert das letzte Signal für einen DataFrame.
    """
    if df is None or df.empty:
        return {
            "signal": "NONE",
            "price": 0.0,
            "time": None,
        }

    work = add_signals(df).dropna(subset=["Close"])
    if work.empty:
        return {
            "signal": "NONE",
            "price": 0.0,
            "time": None,
        }

    last = work.iloc[-1]

    if bool(last.get("buy_signal", False)):
        signal = "BUY"
    elif bool(last.get("sell_signal", False)):
        signal = "SELL"
    else:
        signal = "HOLD"

    return {
        "signal": signal,
        "price": float(last["Close"]),
        "time": str(work.index[-1]),
        "row": last.to_dict(),
    }


def evaluate_open_position(
    position: dict[str, Any],
    df: pd.DataFrame,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """
    Prüft eine bestehende Position gegen die letzte Candle
    und entscheidet SELL oder HOLD.
    """
    sig = latest_signal(df)
    price = float(sig.get("price", 0.0) or 0.0)

    if price <= 0:
        return {
            "action": "HOLD",
            "reason": "NO_PRICE",
            "price": 0.0,
            "time": sig.get("time"),
        }

    entry_price = float(position.get("entry_price", 0.0))
    highest_price = max(float(position.get("highest_price", entry_price)), price)

    stop_loss = _stop_loss_price(entry_price, profile_name=profile_name)
    trailing = _trailing_stop_price(highest_price, profile_name=profile_name)

    if price <= stop_loss:
        return {
            "action": "SELL",
            "reason": "STOP_LOSS",
            "price": price,
            "time": sig.get("time"),
            "highest_price": highest_price,
        }

    if price <= trailing:
        return {
            "action": "SELL",
            "reason": "TRAILING_STOP",
            "price": price,
            "time": sig.get("time"),
            "highest_price": highest_price,
        }

    if sig["signal"] == "SELL":
        return {
            "action": "SELL",
            "reason": "SELL_SIGNAL",
            "price": price,
            "time": sig.get("time"),
            "highest_price": highest_price,
        }

    return {
        "action": "HOLD",
        "reason": "KEEP",
        "price": price,
        "time": sig.get("time"),
        "highest_price": highest_price,
    }


def backtest_symbol_candles(
    symbol: str,
    df: pd.DataFrame,
    capital_eur: float = 200.0,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """
    Candle-by-Candle Backtest für EIN Symbol.
    """
    if df is None or df.empty:
        return {
            "symbol": symbol,
            "trades": [],
            "realized_pnl_eur": 0.0,
            "trade_count": 0,
            "hit_rate_pct": 0.0,
            "equity_curve": [],
        }

    work = add_signals(df).dropna(subset=["Close"])
    if work.empty:
        return {
            "symbol": symbol,
            "trades": [],
            "realized_pnl_eur": 0.0,
            "trade_count": 0,
            "hit_rate_pct": 0.0,
            "equity_curve": [],
        }

    cash = float(capital_eur)
    position: Position | None = None
    trades: list[dict[str, Any]] = []
    equity_curve: list[dict[str, Any]] = []

    for idx, row in work.iterrows():
        price = float(row["Close"])
        ts = str(idx)

        if position is not None:
            position.highest_price = max(position.highest_price, price)

            stop_loss = _stop_loss_price(position.entry_price, profile_name=profile_name)
            trailing = _trailing_stop_price(position.highest_price, profile_name=profile_name)

            sell_reason = None
            if price <= stop_loss:
                sell_reason = "STOP_LOSS"
            elif price <= trailing:
                sell_reason = "TRAILING_STOP"
            elif bool(row.get("sell_signal", False)):
                sell_reason = "SELL_SIGNAL"

            if sell_reason:
                exit_value = position.shares * price
                pnl = exit_value - position.invested_eur
                cash += exit_value

                trades.append(
                    {
                        "symbol": symbol,
                        "buy_time": position.opened_at,
                        "sell_time": ts,
                        "entry_price": position.entry_price,
                        "exit_price": price,
                        "shares": position.shares,
                        "invested_eur": position.invested_eur,
                        "exit_value_eur": exit_value,
                        "pnl_eur": pnl,
                        "reason": sell_reason,
                    }
                )
                position = None

        if position is None and bool(row.get("buy_signal", False)):
            if price > 0 and cash > 0:
                shares = cash / price
                invested = shares * price
                cash -= invested

                position = Position(
                    symbol=symbol,
                    entry_price=price,
                    shares=shares,
                    invested_eur=invested,
                    highest_price=price,
                    opened_at=ts,
                )

        current_equity = cash
        if position is not None:
            current_equity += position.shares * price

        equity_curve.append(
            {
                "time": ts,
                "equity_eur": round(current_equity, 2),
            }
        )

    realized_pnl = sum(float(t["pnl_eur"]) for t in trades)
    wins = sum(1 for t in trades if float(t["pnl_eur"]) > 0)
    trade_count = len(trades)
    hit_rate = (wins / trade_count * 100.0) if trade_count else 0.0

    return {
        "symbol": symbol,
        "trades": trades,
        "realized_pnl_eur": round(realized_pnl, 2),
        "trade_count": trade_count,
        "hit_rate_pct": round(hit_rate, 2),
        "equity_curve": equity_curve,
        "open_position": None
        if position is None
        else {
            "symbol": position.symbol,
            "entry_price": position.entry_price,
            "shares": position.shares,
            "invested_eur": position.invested_eur,
            "highest_price": position.highest_price,
            "opened_at": position.opened_at,
        },
    }
