from __future__ import annotations

from datetime import datetime
from typing import Any

import yfinance as yf

from advanced_risk import (
    adaptive_stop_loss_pct,
    adaptive_trailing_stop_pct,
    calculate_position_budget_from_risk,
)
from candle_backtest import evaluate_open_position, latest_signal
from config import get_active_profile_name, get_trading_config
from performance import analyze_performance
from portfolio_state import (
    append_history_event,
    cash_balance,
    current_positions,
    load_portfolio_state,
    portfolio_summary,
    remove_position,
    save_portfolio_state,
    set_cash_balance,
    set_position,
    update_equity,
)
from risk import may_open_new_positions
from trading_engine import build_trading_plan


DEFAULT_PERIOD = "6mo"
DEFAULT_INTERVAL = "1d"


def _fetch_symbol_data(symbol: str, period: str = DEFAULT_PERIOD, interval: str = DEFAULT_INTERVAL):
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False)
    if df is None or df.empty:
        return None

    if hasattr(df.columns, "levels"):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    return df


def _fetch_all(symbols: list[str], period: str = DEFAULT_PERIOD, interval: str = DEFAULT_INTERVAL) -> dict[str, Any]:
    data = {}
    for symbol in symbols:
        try:
            df = _fetch_symbol_data(symbol, period=period, interval=interval)
            if df is not None and not df.empty:
                data[symbol] = df
        except Exception:
            continue
    return data


def _mark_to_market_equity(state: dict, market_data: dict[str, Any]) -> float:
    equity = cash_balance(state)
    for symbol, pos in current_positions(state).items():
        df = market_data.get(symbol)
        price = float(pos.get("entry_price", 0.0)) if df is None or df.empty else float(df["Close"].iloc[-1])
        equity += float(pos.get("shares", 0.0)) * price
    return float(equity)


def _planned_symbol_lookup(plan: list[dict]) -> dict[str, dict]:
    return {item["symbol"]: item for item in plan}


def _days_open(position: dict) -> int:
    opened = position.get("opened_at")
    if not opened:
        return 999999
    try:
        opened_dt = datetime.fromisoformat(str(opened).replace("Z", "+00:00"))
    except Exception:
        try:
            opened_dt = datetime.strptime(str(opened)[:10], "%Y-%m-%d")
        except Exception:
            return 999999
    now = datetime.now()
    return max(0, (now.date() - opened_dt.date()).days)


def _days_since_exit(state: dict, symbol: str) -> int | None:
    history = state.get("history", [])
    for item in reversed(history):
        if item.get("type") == "SELL" and item.get("symbol") == symbol:
            ts = item.get("time")
            if not ts:
                return None
            try:
                exited_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except Exception:
                try:
                    exited_dt = datetime.strptime(str(ts)[:10], "%Y-%m-%d")
                except Exception:
                    return None
            now = datetime.now()
            return max(0, (now.date() - exited_dt.date()).days)
    return None


def _trades_this_week(state: dict) -> int:
    now = datetime.now()
    iso_now = now.isocalendar()
    count = 0

    for item in state.get("history", []):
        if item.get("type") != "BUY":
            continue
        ts = item.get("time")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            try:
                dt = datetime.strptime(str(ts)[:10], "%Y-%m-%d")
            except Exception:
                continue
        iso = dt.isocalendar()
        if iso.year == iso_now.year and iso.week == iso_now.week:
            count += 1
    return count


def _latest_row_from_df(df):
    if df is None or df.empty:
        return None
    return df.iloc[-1]


def _row_volatility(row) -> float:
    if row is None:
        return 0.0
    try:
        return float(row.get("volatility_20", 0.0) or 0.0)
    except Exception:
        return 0.0


def _expected_edge_pct(row, stop_loss_pct: float, fee_pct: float, slippage_pct: float) -> float:
    if row is None:
        return 0.0
    try:
        momentum = float(row.get("momentum_20", 0.0) or 0.0)
    except Exception:
        momentum = 0.0
    costs = (2.0 * fee_pct) + (2.0 * slippage_pct)
    safety = stop_loss_pct * 0.10
    return max(momentum, 0.0) - costs - safety


def run_mini_trading_system(
    total_capital: float | None = None,
    top_n: int | None = None,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
    profile_name: str | None = None,
) -> dict[str, Any]:
    cfg = get_trading_config(profile_name)

    total_capital = float(total_capital if total_capital is not None else cfg["initial_capital"])
    top_n = int(top_n if top_n is not None else cfg["max_positions"])

    min_hold_days = int(cfg["min_hold_days"])
    cooldown_days = int(cfg["cooldown_days"])
    max_new_trades_per_run = int(cfg["max_new_trades_per_run"])
    max_new_trades_per_week = int(cfg["max_new_trades_per_week"])
    min_learned_score = float(cfg["min_learned_score"])
    max_volatility_20 = float(cfg["max_volatility_20"])
    min_expected_edge_pct = float(cfg["min_expected_edge_pct"])
    fee_pct = float(cfg["fee_pct"])
    slippage_pct = float(cfg["slippage_pct"])
    risk_per_trade_pct = float(cfg["risk_per_trade_pct"])
    max_position_pct = float(cfg["max_position_pct"])
    vol_target = float(cfg["vol_target"])

    state = load_portfolio_state(initial_cash=total_capital)
    perf = analyze_performance()
    plan = build_trading_plan(total_capital=total_capital, top_n=top_n)

    plan_lookup = _planned_symbol_lookup(plan)
    selected_symbols = list(plan_lookup.keys())
    symbols_to_load = sorted(set(selected_symbols) | set(current_positions(state).keys()))
    market_data = _fetch_all(symbols_to_load, period=period, interval=interval)

    current_equity = _mark_to_market_equity(state, market_data)
    can_trade, dd_state = may_open_new_positions(
        current_equity=current_equity,
        peak_equity=state.get("peak_equity_eur"),
    )
    update_equity(state, current_equity)

    orders: list[dict[str, Any]] = []
    new_buys_this_run = 0
    buys_this_week = _trades_this_week(state)

    for symbol, pos in list(current_positions(state).items()):
        df = market_data.get(symbol)
        if df is None or df.empty:
            continue

        check = evaluate_open_position(pos, df)
        price = float(check.get("price", 0.0))
        time_str = check.get("time")
        days_open = _days_open(pos)

        if check["action"] == "SELL":
            if check["reason"] == "SELL_SIGNAL" and days_open < min_hold_days:
                pos["current_price"] = price
                pos["highest_price"] = float(check.get("highest_price", pos.get("highest_price", price)))
                set_position(state, symbol, pos)
                continue

            shares = float(pos.get("shares", 0.0))
            proceeds = shares * price
            pnl = proceeds - float(pos.get("invested_eur", 0.0))

            set_cash_balance(state, cash_balance(state) + proceeds)
            append_history_event(
                state,
                {
                    "type": "SELL",
                    "symbol": symbol,
                    "price": price,
                    "shares": shares,
                    "proceeds_eur": round(proceeds, 2),
                    "pnl_eur": round(pnl, 2),
                    "reason": check["reason"],
                    "bar_time": time_str,
                },
            )
            remove_position(state, symbol)
            orders.append({"action": "SELL", "symbol": symbol, "capital": round(proceeds, 2), "reason": check["reason"]})
        else:
            pos["current_price"] = price
            pos["highest_price"] = float(check.get("highest_price", pos.get("highest_price", price)))
            set_position(state, symbol, pos)

    if can_trade:
        for symbol in selected_symbols:
            if new_buys_this_run >= max_new_trades_per_run:
                break
            if buys_this_week >= max_new_trades_per_week:
                break
            if symbol in current_positions(state):
                continue

            planned = plan_lookup[symbol]
            learned_score = float(planned.get("learned_score", 0.0))
            if learned_score < min_learned_score:
                continue

            days_since_exit = _days_since_exit(state, symbol)
            if days_since_exit is not None and days_since_exit < cooldown_days:
                continue

            df = market_data.get(symbol)
            if df is None or df.empty:
                continue

            sig = latest_signal(df)
            if sig["signal"] != "BUY":
                continue

            row = _latest_row_from_df(df)
            volatility_20 = _row_volatility(row)
            if volatility_20 > max_volatility_20:
                continue

            dynamic_stop_pct = adaptive_stop_loss_pct(
                float(cfg["stop_loss_pct"]),
                volatility_20,
                vol_target,
                float(cfg["adaptive_stop_min_pct"]),
                float(cfg["adaptive_stop_max_pct"]),
            )
            dynamic_trailing_pct = adaptive_trailing_stop_pct(
                float(cfg["trailing_stop_pct"]),
                volatility_20,
                vol_target,
                float(cfg["adaptive_trailing_min_pct"]),
                float(cfg["adaptive_trailing_max_pct"]),
            )

            expected_edge = _expected_edge_pct(row, dynamic_stop_pct, fee_pct, slippage_pct)
            if expected_edge < min_expected_edge_pct:
                continue

            price = float(sig["price"])
            sizing = calculate_position_budget_from_risk(
                current_equity=_mark_to_market_equity(state, market_data),
                cash=cash_balance(state),
                price=price,
                stop_pct=dynamic_stop_pct,
                risk_per_trade_pct=risk_per_trade_pct,
                max_position_pct=max_position_pct,
                fee_pct=fee_pct,
                slippage_pct=slippage_pct,
                min_trade_eur=float(cfg["min_trade_eur"]),
            )

            shares = float(sizing["shares"])
            invested = float(sizing["invested_eur"])
            risk_amount_eur = float(sizing["risk_amount_eur"])

            if shares <= 0 or invested <= 0 or invested > cash_balance(state):
                continue

            set_cash_balance(state, cash_balance(state) - invested)
            set_position(
                state,
                symbol,
                {
                    "symbol": symbol,
                    "entry_price": price,
                    "current_price": price,
                    "highest_price": price,
                    "shares": shares,
                    "invested_eur": invested,
                    "opened_at": sig["time"],
                    "learned_score": learned_score,
                    "stop_loss_pct": dynamic_stop_pct,
                    "trailing_stop_pct": dynamic_trailing_pct,
                    "risk_amount_eur": risk_amount_eur,
                },
            )

            append_history_event(
                state,
                {
                    "type": "BUY",
                    "symbol": symbol,
                    "price": price,
                    "shares": shares,
                    "invested_eur": round(invested, 2),
                    "reason": "BUY_SIGNAL_TOP_SELECTION",
                    "bar_time": sig["time"],
                },
            )

            orders.append({"action": "BUY", "symbol": symbol, "capital": round(invested, 2), "reason": "BUY_SIGNAL_TOP_SELECTION"})
            new_buys_this_run += 1
            buys_this_week += 1

    final_equity = _mark_to_market_equity(state, market_data)
    update_equity(state, final_equity)
    save_portfolio_state(state)

    print("\n========================================")
    print(" MINI TRADING SYSTEM")
    print("========================================")
    print(f"Profil               : {profile_name or get_active_profile_name()}")
    print(f"Zeitpunkt            : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Drawdown blockiert   : {'JA' if dd_state.trading_blocked else 'NEIN'}")
    print(f"Aktueller Equity     : {final_equity:.2f} EUR")
    print("----------------------------------------")
    print(f"Risk pro Trade       : {risk_per_trade_pct:.2%}")
    print(f"Max Position         : {max_position_pct:.2%}")
    print(f"Volatilitätsziel     : {vol_target:.4f}")
    print("----------------------------------------")
    if orders:
        print(f"{'ACT':<6}{'SYM':<8}{'KAPITAL':>14}  REASON")
        print("-" * 60)
        for order in orders:
            print(
                f"{order['action']:<6}"
                f"{order['symbol']:<8}"
                f"{float(order.get('capital', 0.0)):>14.2f} EUR  "
                f"{order.get('reason', '-')}"
            )
    else:
        print("Keine neuen Orders.")
    print("========================================\n")

    return {
        "performance": perf,
        "plan": plan,
        "orders": orders,
        "state": state,
        "equity_eur": final_equity,
        "drawdown_blocked": dd_state.trading_blocked,
        "profile_name": profile_name or get_active_profile_name(),
    }


if __name__ == "__main__":
    run_mini_trading_system()
