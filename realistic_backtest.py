from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import pandas as pd
import yfinance as yf

from advanced_risk import (
    adaptive_stop_loss_pct,
    adaptive_trailing_stop_pct,
    calculate_position_budget_from_risk,
    portfolio_risk_used_pct,
)
from config import (
    REALISTIC_BACKTEST_JSON as DEFAULT_LATEST_JSON,
    REPORTS_DIR as DEFAULT_REPORTS_DIR,
    ensure_reports_dir,
    get_active_profile_name,
    get_trading_config,
)
from performance import analyze_performance
from strategy import add_signals


REPORTS_DIR = DEFAULT_REPORTS_DIR
LATEST_JSON = DEFAULT_LATEST_JSON


@dataclass
class OpenPosition:
    symbol: str
    shares: float
    entry_price: float
    highest_price: float
    invested_eur: float
    entry_date: str
    entry_bar_index: int
    stop_loss_pct: float
    trailing_stop_pct: float
    risk_amount_eur: float


def _ensure_reports_dir() -> None:
    ensure_reports_dir()


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if hasattr(df.columns, "levels"):
        df = df.copy()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df


def _fetch_symbol_data(symbol: str, period: str, interval: str = "1d") -> pd.DataFrame | None:
    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
    )
    if df is None or df.empty:
        return None

    df = _flatten_columns(df)
    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(df.columns):
        return None

    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df = df.dropna(subset=["Close"])
    if df.empty:
        return None

    return add_signals(df)


def _fetch_market_data(symbols: list[str], period: str, interval: str = "1d") -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        try:
            df = _fetch_symbol_data(symbol, period=period, interval=interval)
            if df is not None and not df.empty:
                out[symbol] = df
        except Exception:
            continue
    return out


def _build_calendar(data: dict[str, pd.DataFrame]) -> list[pd.Timestamp]:
    idx = set()
    for df in data.values():
        idx.update(df.index.tolist())
    return sorted(idx)


def _score_lookup() -> dict[str, float]:
    stats = analyze_performance()
    lookup: dict[str, float] = {}
    for row in stats.get("ranking", []):
        lookup[row["symbol"]] = float(row.get("learned_score", 0.0))
    return lookup


def _pick_symbols(explicit_symbols: list[str] | None, top_n: int) -> list[str]:
    if explicit_symbols:
        cleaned = [s for s in explicit_symbols if s]
        if cleaned:
            return cleaned[:top_n]

    stats = analyze_performance()
    ranking = stats.get("ranking", [])
    return [row["symbol"] for row in ranking[:top_n] if row.get("symbol")]


def _mark_to_market_equity(
    cash: float,
    positions: dict[str, OpenPosition],
    candle_rows: dict[str, pd.Series],
) -> float:
    equity = float(cash)
    for symbol, pos in positions.items():
        row = candle_rows.get(symbol)
        price = pos.entry_price if row is None else float(row["Close"])
        equity += pos.shares * price
    return equity


def _max_drawdown_pct(equity_curve: list[dict[str, Any]]) -> float:
    if not equity_curve:
        return 0.0

    peak = float(equity_curve[0]["equity_eur"])
    max_dd = 0.0

    for point in equity_curve:
        value = float(point["equity_eur"])
        peak = max(peak, value)
        if peak > 0:
            dd = (peak - value) / peak * 100.0
            max_dd = max(max_dd, dd)

    return max_dd


def _annualized_return(initial: float, final: float, days: int) -> float:
    if initial <= 0 or final <= 0 or days <= 0:
        return 0.0
    years = days / 365.25
    if years <= 0:
        return 0.0
    return ((final / initial) ** (1 / years) - 1.0) * 100.0


def _week_key(ts: pd.Timestamp) -> str:
    iso = ts.to_pydatetime().isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _row_volatility(row: pd.Series) -> float:
    if "volatility_20" in row and pd.notna(row["volatility_20"]):
        try:
            value = float(row["volatility_20"])
            return value / 100.0 if value > 1.0 else value
        except Exception:
            pass
    return 0.0


def _expected_edge_pct(
    row: pd.Series,
    stop_loss_pct: float,
    fee_pct: float,
    slippage_pct: float,
) -> float:
    momentum = 0.0
    if "momentum_20" in row and pd.notna(row["momentum_20"]):
        try:
            momentum = float(row["momentum_20"])
        except Exception:
            momentum = 0.0

    raw_edge = max(momentum, 0.0)
    costs = (2.0 * fee_pct) + (2.0 * slippage_pct)
    safety = stop_loss_pct * 0.10
    return raw_edge - costs - safety


def run_realistic_backtest(
    symbols: list[str] | None = None,
    period: str = "1y",
    interval: str = "1d",
    profile_name: str | None = None,
    **overrides,
) -> dict[str, Any]:
    _ensure_reports_dir()

    cfg = get_trading_config(profile_name)
    cfg.update(overrides)

    initial_capital = float(cfg["initial_capital"])
    max_positions = int(cfg["max_positions"])
    fee_pct = float(cfg["fee_pct"])
    slippage_pct = float(cfg["slippage_pct"])
    base_stop_loss_pct = float(cfg["stop_loss_pct"])
    base_trailing_stop_pct = float(cfg["trailing_stop_pct"])
    min_trade_eur = float(cfg["min_trade_eur"])
    min_hold_bars = int(cfg["min_hold_bars"])
    cooldown_bars = int(cfg["cooldown_bars"])
    max_new_trades_per_bar = int(cfg["max_new_trades_per_bar"])
    max_new_trades_per_week = int(cfg["max_new_trades_per_week"])
    min_learned_score = float(cfg["min_learned_score"])
    max_volatility_20 = float(cfg["max_volatility_20"])
    min_stop_distance_pct = float(cfg["min_stop_distance_pct"])
    min_expected_edge_pct = float(cfg["min_expected_edge_pct"])
    risk_per_trade_pct = float(cfg["risk_per_trade_pct"])
    max_position_pct = float(cfg["max_position_pct"])
    max_portfolio_risk_pct = float(cfg["max_portfolio_risk_pct"])
    vol_target = float(cfg["vol_target"])
    adaptive_stop_min_pct = float(cfg["adaptive_stop_min_pct"])
    adaptive_stop_max_pct = float(cfg["adaptive_stop_max_pct"])
    adaptive_trailing_min_pct = float(cfg["adaptive_trailing_min_pct"])
    adaptive_trailing_max_pct = float(cfg["adaptive_trailing_max_pct"])

    selected_symbols = _pick_symbols(symbols, top_n=max_positions)
    learned_scores = _score_lookup()
    data = _fetch_market_data(selected_symbols, period=period, interval=interval)
    selected_symbols = [s for s in selected_symbols if s in data]

    base_result = {
        "period": period,
        "interval": interval,
        "profile_name": profile_name or get_active_profile_name(),
        "initial_capital": initial_capital,
        "anti_overtrading": {
            "min_hold_bars": min_hold_bars,
            "cooldown_bars": cooldown_bars,
            "max_new_trades_per_bar": max_new_trades_per_bar,
            "max_new_trades_per_week": max_new_trades_per_week,
            "min_learned_score": min_learned_score,
            "max_volatility_20": max_volatility_20,
            "min_stop_distance_pct": min_stop_distance_pct,
            "min_expected_edge_pct": min_expected_edge_pct,
            "risk_per_trade_pct": risk_per_trade_pct,
            "max_position_pct": max_position_pct,
            "max_portfolio_risk_pct": max_portfolio_risk_pct,
            "vol_target": vol_target,
        },
    }

    if not selected_symbols:
        result = {
            **base_result,
            "final_equity": initial_capital,
            "total_return_pct": 0.0,
            "cagr_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "fees_paid_eur": 0.0,
            "slippage_paid_eur": 0.0,
            "trade_count": 0,
            "win_rate_pct": 0.0,
            "symbols": [],
            "equity_curve": [],
            "trades": [],
            "note": "Keine Daten verfügbar.",
        }
        with open(LATEST_JSON, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        return result

    calendar = _build_calendar(data)
    if not calendar:
        result = {
            **base_result,
            "final_equity": initial_capital,
            "total_return_pct": 0.0,
            "cagr_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "fees_paid_eur": 0.0,
            "slippage_paid_eur": 0.0,
            "trade_count": 0,
            "win_rate_pct": 0.0,
            "symbols": selected_symbols,
            "equity_curve": [],
            "trades": [],
            "note": "Kalender leer.",
        }
        with open(LATEST_JSON, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        return result

    cash = float(initial_capital)
    positions: dict[str, OpenPosition] = {}
    trades: list[dict[str, Any]] = []
    equity_curve: list[dict[str, Any]] = []

    total_fees = 0.0
    total_slippage = 0.0
    last_exit_bar_by_symbol: dict[str, int] = {}
    trades_per_week: dict[str, int] = {}

    for bar_index, ts in enumerate(calendar):
        candle_rows: dict[str, pd.Series] = {}
        new_trades_this_bar = 0
        week_key = _week_key(ts)
        trades_per_week.setdefault(week_key, 0)

        for symbol, df in data.items():
            if ts in df.index:
                candle_rows[symbol] = df.loc[ts]

        for symbol in list(positions.keys()):
            pos = positions[symbol]
            row = candle_rows.get(symbol)
            if row is None:
                continue

            market_price = float(row["Close"])
            pos.highest_price = max(pos.highest_price, market_price)

            stop_loss_price = pos.entry_price * (1.0 - pos.stop_loss_pct)
            trailing_stop_price = pos.highest_price * (1.0 - pos.trailing_stop_pct)
            held_bars = bar_index - pos.entry_bar_index

            exit_reason = None
            if market_price <= stop_loss_price:
                exit_reason = "STOP_LOSS"
            elif market_price <= trailing_stop_price:
                exit_reason = "TRAILING_STOP"
            elif held_bars >= min_hold_bars and bool(row.get("sell_signal", False)):
                exit_reason = "SELL_SIGNAL"

            if exit_reason:
                exit_price = market_price * (1.0 - slippage_pct)
                gross_value = pos.shares * exit_price
                fee = gross_value * fee_pct
                proceeds = gross_value - fee

                slippage_cost = pos.shares * market_price - gross_value
                total_fees += fee
                total_slippage += max(0.0, slippage_cost)

                pnl = proceeds - pos.invested_eur
                cash += proceeds
                last_exit_bar_by_symbol[symbol] = bar_index

                trades.append(
                    {
                        "symbol": symbol,
                        "entry_date": pos.entry_date,
                        "exit_date": str(ts),
                        "entry_price": round(pos.entry_price, 4),
                        "exit_price": round(exit_price, 4),
                        "shares": round(pos.shares, 6),
                        "invested_eur": round(pos.invested_eur, 2),
                        "proceeds_eur": round(proceeds, 2),
                        "pnl_eur": round(pnl, 2),
                        "reason": exit_reason,
                        "held_bars": held_bars,
                        "risk_amount_eur": round(pos.risk_amount_eur, 2),
                    }
                )
                del positions[symbol]

        if len(positions) < max_positions and cash >= min_trade_eur:
            buy_candidates: list[tuple[float, str, float, float, float, float]] = []

            for symbol in selected_symbols:
                if symbol in positions:
                    continue

                row = candle_rows.get(symbol)
                if row is None:
                    continue

                score = float(learned_scores.get(symbol, 0.0))
                if score < min_learned_score:
                    continue

                last_exit_bar = last_exit_bar_by_symbol.get(symbol)
                if last_exit_bar is not None and (bar_index - last_exit_bar) < cooldown_bars:
                    continue

                if trades_per_week[week_key] >= max_new_trades_per_week:
                    break

                if not bool(row.get("buy_signal", False)):
                    continue

                market_price = float(row["Close"])
                volatility_20 = _row_volatility(row)
                if volatility_20 > max_volatility_20:
                    continue

                dynamic_stop_pct = adaptive_stop_loss_pct(
                    base_stop_loss_pct,
                    volatility_20,
                    vol_target,
                    adaptive_stop_min_pct,
                    adaptive_stop_max_pct,
                )
                dynamic_trailing_pct = adaptive_trailing_stop_pct(
                    base_trailing_stop_pct,
                    volatility_20,
                    vol_target,
                    adaptive_trailing_min_pct,
                    adaptive_trailing_max_pct,
                )

                if dynamic_stop_pct < min_stop_distance_pct:
                    continue

                expected_edge_pct = _expected_edge_pct(
                    row=row,
                    stop_loss_pct=dynamic_stop_pct,
                    fee_pct=fee_pct,
                    slippage_pct=slippage_pct,
                )
                if expected_edge_pct < min_expected_edge_pct:
                    continue

                buy_candidates.append(
                    (score, symbol, market_price, expected_edge_pct, dynamic_stop_pct, dynamic_trailing_pct)
                )

            buy_candidates.sort(reverse=True, key=lambda x: (x[0], x[3]))

            for _, symbol, market_price, _, dynamic_stop_pct, dynamic_trailing_pct in buy_candidates:
                if len(positions) >= max_positions:
                    break
                if new_trades_this_bar >= max_new_trades_per_bar:
                    break
                if trades_per_week[week_key] >= max_new_trades_per_week:
                    break

                current_equity = _mark_to_market_equity(cash, positions, candle_rows)
                current_risk_pct = portfolio_risk_used_pct(
                    {k: vars(v) for k, v in positions.items()},
                    current_equity,
                )
                if current_risk_pct >= max_portfolio_risk_pct:
                    break

                sizing = calculate_position_budget_from_risk(
                    current_equity=current_equity,
                    cash=cash,
                    price=market_price,
                    stop_pct=dynamic_stop_pct,
                    risk_per_trade_pct=risk_per_trade_pct,
                    max_position_pct=max_position_pct,
                    fee_pct=fee_pct,
                    slippage_pct=slippage_pct,
                    min_trade_eur=min_trade_eur,
                )

                shares = float(sizing["shares"])
                total_cost = float(sizing["invested_eur"])
                risk_amount_eur = float(sizing["risk_amount_eur"])

                if shares <= 0 or total_cost <= 0 or total_cost > cash:
                    continue

                entry_price = market_price * (1.0 + slippage_pct)
                gross_cost = shares * entry_price
                fee = gross_cost * fee_pct
                slippage_cost = gross_cost - (shares * market_price)

                total_fees += fee
                total_slippage += max(0.0, slippage_cost)
                cash -= total_cost

                positions[symbol] = OpenPosition(
                    symbol=symbol,
                    shares=shares,
                    entry_price=entry_price,
                    highest_price=market_price,
                    invested_eur=total_cost,
                    entry_date=str(ts),
                    entry_bar_index=bar_index,
                    stop_loss_pct=dynamic_stop_pct,
                    trailing_stop_pct=dynamic_trailing_pct,
                    risk_amount_eur=risk_amount_eur,
                )
                new_trades_this_bar += 1
                trades_per_week[week_key] += 1

        equity = _mark_to_market_equity(cash, positions, candle_rows)
        equity_curve.append(
            {
                "time": str(ts),
                "equity_eur": round(equity, 2),
                "cash_eur": round(cash, 2),
                "open_positions": len(positions),
            }
        )

    final_equity = equity_curve[-1]["equity_eur"] if equity_curve else initial_capital
    trade_count = len(trades)
    wins = sum(1 for t in trades if float(t["pnl_eur"]) > 0)
    win_rate = (wins / trade_count * 100.0) if trade_count else 0.0
    total_return_pct = ((final_equity / initial_capital) - 1.0) * 100.0 if initial_capital > 0 else 0.0
    max_drawdown = _max_drawdown_pct(equity_curve)

    days = 0
    if len(calendar) >= 2:
        days = max(1, (calendar[-1] - calendar[0]).days)
    cagr_pct = _annualized_return(initial_capital, final_equity, days)

    result = {
        **base_result,
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return_pct, 2),
        "cagr_pct": round(cagr_pct, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "fees_paid_eur": round(total_fees, 2),
        "slippage_paid_eur": round(total_slippage, 2),
        "trade_count": trade_count,
        "win_rate_pct": round(win_rate, 2),
        "symbols": selected_symbols,
        "equity_curve": equity_curve,
        "trades": trades,
    }

    with open(LATEST_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


def print_realistic_backtest_summary(result: dict[str, Any]) -> None:
    print("\n========================================")
    print(" REALISTISCHE 10.000-EUR-SCHÄTZUNG")
    print("========================================")
    print(f"Profil              : {result.get('profile_name', '-')}")
    print(f"Zeitraum            : {result.get('period', '-')}")
    print(f"Intervall           : {result.get('interval', '-')}")
    print(f"Startkapital        : {float(result.get('initial_capital', 0.0)):,.2f} EUR")
    print(f"Endkapital          : {float(result.get('final_equity', 0.0)):,.2f} EUR")
    print(f"Gesamtrendite       : {float(result.get('total_return_pct', 0.0)):.2f}%")
    print(f"CAGR                : {float(result.get('cagr_pct', 0.0)):.2f}%")
    print(f"Max Drawdown        : {float(result.get('max_drawdown_pct', 0.0)):.2f}%")
    print(f"Trades              : {int(result.get('trade_count', 0))}")
    print(f"Trefferquote        : {float(result.get('win_rate_pct', 0.0)):.2f}%")
    print(f"Gebühren gesamt     : {float(result.get('fees_paid_eur', 0.0)):,.2f} EUR")
    print(f"Slippage gesamt     : {float(result.get('slippage_paid_eur', 0.0)):,.2f} EUR")
    print("----------------------------------------")
    anti = result.get("anti_overtrading", {})
    if anti:
        print(f"Mindesthaltedauer   : {anti.get('min_hold_bars', '-')}")
        print(f"Cooldown nach Exit  : {anti.get('cooldown_bars', '-')}")
        print(f"Max neue Trades/Tag : {anti.get('max_new_trades_per_bar', '-')}")
        print(f"Max Trades/Woche    : {anti.get('max_new_trades_per_week', '-')}")
        print(f"Risk/Trade          : {float(anti.get('risk_per_trade_pct', 0.0)):.2%}")
        print(f"Max Position        : {float(anti.get('max_position_pct', 0.0)):.2%}")
        print(f"Max Portfolio-Risk  : {float(anti.get('max_portfolio_risk_pct', 0.0)):.2%}")
        print(f"Vol-Ziel            : {float(anti.get('vol_target', 0.0)):.4f}")
    symbols = result.get("symbols", [])
    if symbols:
        print("Verwendete Symbole  : " + ", ".join(symbols))
    print("========================================\n")
