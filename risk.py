from dataclasses import dataclass


MAX_POSITION_PCT = 0.20       # max. 20% Kapital pro Aktie
STOP_LOSS_PCT = 0.05          # 5% Stop-Loss
TRAILING_STOP_PCT = 0.08      # 8% Trailing Stop
MAX_DRAWDOWN_PCT = 0.15       # 15% maximaler Portfolio-Drawdown
MIN_POSITION_EUR = 25.0       # unterhalb davon keine neue Position


@dataclass
class DrawdownState:
    peak_equity: float
    current_equity: float
    drawdown_pct: float
    trading_blocked: bool


def max_position_eur(total_capital: float) -> float:
    return float(total_capital) * MAX_POSITION_PCT


def clamp_position_capital(capital: float, total_capital: float) -> float:
    capped = min(float(capital), max_position_eur(total_capital))
    return max(0.0, capped)


def stop_loss_price(entry_price: float) -> float:
    return float(entry_price) * (1.0 - STOP_LOSS_PCT)


def trailing_stop_price(highest_price: float) -> float:
    return float(highest_price) * (1.0 - TRAILING_STOP_PCT)


def compute_drawdown_state(current_equity: float, peak_equity: float | None = None) -> DrawdownState:
    current_equity = float(current_equity)

    if peak_equity is None:
        peak_equity = current_equity

    peak_equity = max(float(peak_equity), current_equity)

    if peak_equity <= 0:
        drawdown_pct = 0.0
    else:
        drawdown_pct = (peak_equity - current_equity) / peak_equity

    return DrawdownState(
        peak_equity=peak_equity,
        current_equity=current_equity,
        drawdown_pct=drawdown_pct,
        trading_blocked=drawdown_pct >= MAX_DRAWDOWN_PCT,
    )


def may_open_new_positions(current_equity: float, peak_equity: float | None = None) -> tuple[bool, DrawdownState]:
    state = compute_drawdown_state(current_equity=current_equity, peak_equity=peak_equity)
    return (not state.trading_blocked), state


def risk_summary() -> dict:
    return {
        "max_position_pct": MAX_POSITION_PCT,
        "stop_loss_pct": STOP_LOSS_PCT,
        "trailing_stop_pct": TRAILING_STOP_PCT,
        "max_drawdown_pct": MAX_DRAWDOWN_PCT,
        "min_position_eur": MIN_POSITION_EUR,
    }
