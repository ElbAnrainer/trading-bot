from __future__ import annotations

from typing import Any

from config import get_trading_config
from performance import analyze_performance
from risk import (
    clamp_position_capital,
    min_position_eur,
    may_open_new_positions,
    risk_summary,
    stop_loss_price,
)


def _positive_score(value: float) -> float:
    return max(float(value), 0.0)


def _score_weighted_selection(ranking: list[dict], top_n: int) -> list[dict]:
    positive = [r for r in ranking if _positive_score(r.get("learned_score", 0.0)) > 0]
    selected = positive[:top_n]
    if selected:
        return selected
    return ranking[:top_n]


def _allocate_capped_capital(
    selected: list[dict],
    total_capital: float,
    profile_name: str | None = None,
) -> list[dict]:
    if not selected:
        return []

    total_capital = float(total_capital)
    risk = risk_summary(profile_name)
    scores = [_positive_score(item.get("learned_score", 0.0)) for item in selected]
    score_sum = sum(scores)

    if score_sum <= 0:
        base = total_capital / len(selected)
        out = []
        for item in selected:
            capital = clamp_position_capital(base, total_capital, profile_name=profile_name)
            out.append(
                {
                    **item,
                    "weight": capital / total_capital if total_capital > 0 else 0.0,
                    "capital": round(capital, 2),
                }
            )
        return out

    remaining_capital = total_capital
    remaining_idx = set(range(len(selected)))
    allocations = [0.0 for _ in selected]
    capped_limit = total_capital * float(risk["max_position_pct"])

    # Iterative capped allocation
    while remaining_idx and remaining_capital > 0:
        remaining_score_sum = sum(scores[i] for i in remaining_idx)
        if remaining_score_sum <= 0:
            equal_share = remaining_capital / len(remaining_idx)
            for i in list(remaining_idx):
                allocation = min(equal_share, capped_limit - allocations[i])
                allocations[i] += max(0.0, allocation)
            break

        changed = False
        for i in list(remaining_idx):
            raw_share = remaining_capital * (scores[i] / remaining_score_sum)
            room = capped_limit - allocations[i]
            allocation = min(raw_share, room)

            if allocation > 0:
                allocations[i] += allocation
                changed = True

            if allocations[i] >= capped_limit - 1e-9:
                remaining_idx.remove(i)

        distributed = sum(allocations)
        remaining_capital = max(0.0, total_capital - distributed)

        if not changed:
            break

    out = []
    for item, capital in zip(selected, allocations):
        capital = clamp_position_capital(capital, total_capital, profile_name=profile_name)
        if capital < min_position_eur(profile_name):
            continue
        out.append(
            {
                **item,
                "weight": capital / total_capital if total_capital > 0 else 0.0,
                "capital": round(capital, 2),
            }
        )

    return out


def build_trading_plan(
    total_capital: float = 1000.0,
    top_n: int | None = 5,
    profile_name: str | None = None,
) -> list[dict]:
    stats = analyze_performance()
    ranking = stats.get("ranking", [])
    cfg = get_trading_config(profile_name)

    if not ranking:
        return []

    max_positions = max(0, int(cfg.get("max_positions", 0)))
    if top_n is None:
        effective_top_n = max_positions
    else:
        effective_top_n = min(max(0, int(top_n)), max_positions)

    if effective_top_n <= 0:
        return []

    selected = _score_weighted_selection(ranking, top_n=effective_top_n)
    return _allocate_capped_capital(selected, total_capital=total_capital, profile_name=profile_name)


def _learned_score_lookup() -> dict[str, float]:
    stats = analyze_performance()
    lookup = {}
    for item in stats.get("ranking", []):
        lookup[item["symbol"]] = float(item.get("learned_score", 0.0))
    return lookup


def simulate_trading_decisions(
    analysis_result: dict[str, Any],
    total_capital: float = 1000.0,
    current_positions: dict[str, dict] | None = None,
    peak_equity: float | None = None,
    top_n: int | None = None,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """
    Erwartet analysis_result aus run_analysis().
    Nutzt future_candidates/results + learned_score + Drawdown-Control.
    """
    current_positions = current_positions or {}

    perf_stats = analyze_performance()
    current_equity = float(total_capital) + float(perf_stats.get("realized_pnl", 0.0))

    can_trade, dd_state = may_open_new_positions(
        current_equity=current_equity,
        peak_equity=peak_equity,
        profile_name=profile_name,
    )

    learned_scores = _learned_score_lookup()
    desired_plan = build_trading_plan(
        total_capital=total_capital,
        top_n=top_n,
        profile_name=profile_name,
    )
    desired_symbols = {item["symbol"] for item in desired_plan}

    candidates = analysis_result.get("future_candidates", [])
    candidate_by_symbol = {c["symbol"]: c for c in candidates}

    orders: list[dict[str, Any]] = []

    # SELL / CLOSE zuerst
    for symbol, pos in current_positions.items():
        signal = candidate_by_symbol.get(symbol, {}).get("future_signal", "SELL")
        current_price = float(pos.get("current_price", pos.get("entry_price", 0.0)))
        entry_price = float(pos.get("entry_price", 0.0))

        stop_loss_triggered = False
        if entry_price > 0 and current_price > 0:
            stop_loss_triggered = current_price <= stop_loss_price(
                entry_price,
                profile_name=profile_name,
            )

        if symbol not in desired_symbols or signal == "SELL" or stop_loss_triggered:
            reason = "SELL_SIGNAL"
            if symbol not in desired_symbols:
                reason = "NOT_IN_TOP_SELECTION"
            if stop_loss_triggered:
                reason = "STOP_LOSS"

            orders.append(
                {
                    "action": "SELL",
                    "symbol": symbol,
                    "reason": reason,
                    "capital": round(float(pos.get("capital", 0.0)), 2),
                    "learned_score": learned_scores.get(symbol, 0.0),
                }
            )

    # BUY danach
    if can_trade:
        for planned in desired_plan:
            symbol = planned["symbol"]
            if symbol in current_positions:
                continue

            candidate = candidate_by_symbol.get(symbol)
            signal = candidate.get("future_signal") if candidate else "WATCH"

            if signal not in ("BUY", "WATCH"):
                continue

            orders.append(
                {
                    "action": "BUY",
                    "symbol": symbol,
                    "reason": f"{signal}_TOP_SELECTION",
                    "capital": round(float(planned["capital"]), 2),
                    "weight": round(float(planned["weight"]), 4),
                    "learned_score": learned_scores.get(symbol, planned.get("learned_score", 0.0)),
                }
            )

    return {
        "orders": orders,
        "drawdown_state": {
            "peak_equity": dd_state.peak_equity,
            "current_equity": dd_state.current_equity,
            "drawdown_pct": dd_state.drawdown_pct,
            "trading_blocked": dd_state.trading_blocked,
        },
        "risk": risk_summary(profile_name),
    }


def print_trading_plan(plan: list[dict]) -> None:
    print("\n========================================")
    print(" TRADING PLAN (REAL)")
    print("========================================")

    if not plan:
        print("Kein Trading-Plan verfügbar.")
        print("========================================\n")
        return

    print(f"{'SYM':<6}{'GEWICHT':>10}{'KAPITAL':>14}{'SCORE':>14}")
    print("-" * 44)

    for p in plan:
        print(
            f"{p['symbol']:<6}"
            f"{p['weight']:>10.2f}"
            f"{p['capital']:>14.2f} EUR"
            f"{p['learned_score']:>14.2f}"
        )

    print("========================================\n")


def print_trading_decisions(decisions: dict[str, Any]) -> None:
    dd = decisions["drawdown_state"]

    print("\n========================================")
    print(" ENTRY / EXIT ENGINE")
    print("========================================")
    print(f"Aktueller Equity-Stand : {dd['current_equity']:.2f} EUR")
    print(f"Peak Equity            : {dd['peak_equity']:.2f} EUR")
    print(f"Drawdown               : {dd['drawdown_pct'] * 100:.2f}%")
    print(f"Trading blockiert      : {'JA' if dd['trading_blocked'] else 'NEIN'}")
    print("----------------------------------------")

    orders = decisions.get("orders", [])
    if not orders:
        print("Keine Orders erzeugt.")
        print("========================================\n")
        return

    print(f"{'ACT':<6}{'SYM':<8}{'KAPITAL':>14}{'SCORE':>14}  REASON")
    print("-" * 72)

    for order in orders:
        print(
            f"{order['action']:<6}"
            f"{order['symbol']:<8}"
            f"{float(order.get('capital', 0.0)):>14.2f} EUR"
            f"{float(order.get('learned_score', 0.0)):>14.2f}  "
            f"{order.get('reason', '-')}"
        )

    print("========================================\n")
