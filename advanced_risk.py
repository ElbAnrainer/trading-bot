from __future__ import annotations

from typing import Any


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def adaptive_stop_loss_pct(
    base_stop_pct: float,
    volatility_20: float,
    vol_target: float,
    min_stop_pct: float,
    max_stop_pct: float,
) -> float:
    if volatility_20 <= 0 or vol_target <= 0:
        return clamp(base_stop_pct, min_stop_pct, max_stop_pct)

    scale = volatility_20 / vol_target
    adjusted = base_stop_pct * scale
    return clamp(adjusted, min_stop_pct, max_stop_pct)


def adaptive_trailing_stop_pct(
    base_trailing_pct: float,
    volatility_20: float,
    vol_target: float,
    min_trailing_pct: float,
    max_trailing_pct: float,
) -> float:
    if volatility_20 <= 0 or vol_target <= 0:
        return clamp(base_trailing_pct, min_trailing_pct, max_trailing_pct)

    scale = volatility_20 / vol_target
    adjusted = base_trailing_pct * scale
    return clamp(adjusted, min_trailing_pct, max_trailing_pct)


def portfolio_risk_used_pct(
    positions: dict[str, Any],
    current_equity: float,
) -> float:
    if current_equity <= 0:
        return 0.0

    total_risk = 0.0
    for pos in positions.values():
        total_risk += float(pos.get("risk_amount_eur", 0.0))

    return total_risk / current_equity


def calculate_position_budget_from_risk(
    current_equity: float,
    cash: float,
    price: float,
    stop_pct: float,
    risk_per_trade_pct: float,
    max_position_pct: float,
    fee_pct: float,
    slippage_pct: float,
    min_trade_eur: float,
) -> dict[str, float]:
    """
    Positionsgröße aus Risiko.
    risk_amount = equity * risk_per_trade_pct
    shares = risk_amount / (price * stop_pct)
    Danach Deckelung über max_position_pct und verfügbares Cash.
    """
    if current_equity <= 0 or cash <= 0 or price <= 0 or stop_pct <= 0:
        return {"shares": 0.0, "invested_eur": 0.0, "risk_amount_eur": 0.0}

    risk_amount = current_equity * risk_per_trade_pct
    raw_shares = risk_amount / (price * stop_pct)

    entry_price = price * (1.0 + slippage_pct)
    gross_cost = raw_shares * entry_price
    fee = gross_cost * fee_pct
    total_cost = gross_cost + fee

    max_position_eur = current_equity * max_position_pct
    allowed_budget = min(cash, max_position_eur)

    if total_cost > allowed_budget and total_cost > 0:
        scale = allowed_budget / total_cost
        raw_shares *= scale
        gross_cost = raw_shares * entry_price
        fee = gross_cost * fee_pct
        total_cost = gross_cost + fee

    if total_cost < min_trade_eur:
        return {"shares": 0.0, "invested_eur": 0.0, "risk_amount_eur": 0.0}

    actual_risk_amount = raw_shares * price * stop_pct
    return {
        "shares": max(0.0, raw_shares),
        "invested_eur": max(0.0, total_cost),
        "risk_amount_eur": max(0.0, actual_risk_amount),
    }
