"""Primary walk-forward engine used by ``main.py``.

This module runs the current portfolio-style walk-forward simulation across
predefined windows and is the implementation that powers the integrated CLI.
It intentionally differs from ``walk_forward.py``, which is kept as a legacy
report-oriented entry point for compatibility with older scripts and workflow
automation.
"""

from __future__ import annotations

import copy
from typing import Any

from analysis_engine import run_analysis
from trading_engine import simulate_trading_decisions


# =========================================================
# KONFIG
# =========================================================

WALK_WINDOWS = [
    "1mo",
    "3mo",
    "6mo",
    "1y",
    "2y",
]


# =========================================================
# HELPERS
# =========================================================

def _empty_portfolio() -> dict:
    return {}


def _apply_orders(portfolio: dict, orders: list[dict], prices: dict[str, float]) -> tuple[dict, float]:
    """
    Führt Orders aus und berechnet P/L
    """
    portfolio = copy.deepcopy(portfolio)
    realized_pnl = 0.0

    for order in orders:
        symbol = order["symbol"]
        action = order["action"]

        if action == "BUY":
            if symbol in portfolio:
                continue

            price = prices.get(symbol, 0.0)
            if price <= 0:
                continue

            capital = float(order.get("capital", 0.0))
            shares = capital / price if price > 0 else 0

            portfolio[symbol] = {
                "entry_price": price,
                "shares": shares,
                "capital": capital,
                "current_price": price,
            }

        elif action == "SELL":
            if symbol not in portfolio:
                continue

            pos = portfolio[symbol]
            entry_price = pos["entry_price"]
            shares = pos["shares"]

            price = prices.get(symbol, entry_price)

            pnl = (price - entry_price) * shares
            realized_pnl += pnl

            del portfolio[symbol]

    return portfolio, realized_pnl


def _extract_prices(result: dict[str, Any]) -> dict[str, float]:
    """
    Holt aktuelle Preise aus Analyse
    """
    prices = {}

    for r in result.get("results", []):
        symbol = r["symbol"]
        price = r.get("price") or r.get("close") or 0.0
        prices[symbol] = float(price)

    return prices


# =========================================================
# CORE WALK-FORWARD
# =========================================================

def run_walk_forward(total_capital: float = 1000.0) -> dict:
    print("\n========================================")
    print(" WALK-FORWARD ANALYSE")
    print("========================================")

    portfolio = _empty_portfolio()
    peak_equity = total_capital

    equity = total_capital
    equity_curve = []

    all_pnl = []
    wins = 0
    trades = 0

    for i, period in enumerate(WALK_WINDOWS, start=1):
        print(f">>> Starte Walk-Forward-Fenster {period}")

        result = run_analysis(
            period=period,
            top_n=5,
            min_volume=1_000_000,
            long_mode=True,
            show_progress=False,
        )

        prices = _extract_prices(result)

        decisions = simulate_trading_decisions(
            analysis_result=result,
            total_capital=equity,
            current_positions=portfolio,
            peak_equity=peak_equity,
        )

        orders = decisions["orders"]

        # Orders ausführen
        portfolio, pnl = _apply_orders(portfolio, orders, prices)

        equity += pnl
        peak_equity = max(peak_equity, equity)

        equity_curve.append({
            "run": i,
            "period": period,
            "equity": equity,
            "pnl": pnl,
        })

        all_pnl.append(pnl)

        if pnl > 0:
            wins += 1
        if orders:
            trades += len(orders)

        print(f"Run {i} | P/L {pnl:.2f} | Equity {equity:.2f}")

    # =========================================================
    # AUSWERTUNG
    # =========================================================

    avg_pnl = sum(all_pnl) / len(all_pnl) if all_pnl else 0.0
    hit_rate = (wins / len(all_pnl)) * 100 if all_pnl else 0.0

    print("\n----------------------------------------")
    print(f"Ø P/L        : {avg_pnl:.2f}")
    print(f"Ø Treffer    : {hit_rate:.2f}%")
    print(f"Trades       : {trades}")
    print("----------------------------------------")

    return {
        "equity_curve": equity_curve,
        "avg_pnl": avg_pnl,
        "hit_rate": hit_rate,
        "trades": trades,
    }
