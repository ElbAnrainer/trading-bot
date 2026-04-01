import json
import os
from datetime import datetime


FILE = "reports/portfolio_state.json"


def _ensure():
    os.makedirs("reports", exist_ok=True)


def load_portfolio_state(initial_cash=1000.0):
    _ensure()

    if not os.path.exists(FILE):
        return {
            "cash": initial_cash,
            "positions": {},
            "peak": initial_cash,
        }

    with open(FILE, "r") as f:
        return json.load(f)


def save_portfolio_state(state):
    _ensure()
    state["updated"] = datetime.now().isoformat()

    with open(FILE, "w") as f:
        json.dump(state, f, indent=2)


def current_positions(state):
    return state.get("positions", {})


def set_position(state, symbol, pos):
    state.setdefault("positions", {})[symbol] = pos


def remove_position(state, symbol):
    state.setdefault("positions", {}).pop(symbol, None)


def cash_balance(state):
    return float(state.get("cash", 0.0))


def set_cash_balance(state, value):
    state["cash"] = float(value)


def update_equity(state, equity):
    state["peak"] = max(state.get("peak", equity), equity)


def append_history_event(state, event):
    state.setdefault("history", []).append(event)


def portfolio_summary(state):
    return {
        "cash_eur": state.get("cash", 0),
        "positions": len(state.get("positions", {})),
        "total_invested_eur": sum(
            p.get("invested_eur", 0)
            for p in state.get("positions", {}).values()
        ),
    }
