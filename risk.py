from dataclasses import dataclass

from config import get_trading_config

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


def _risk_config(profile_name: str | None = None) -> dict[str, float]:
    cfg = {
        "max_position_pct": MAX_POSITION_PCT,
        "stop_loss_pct": STOP_LOSS_PCT,
        "trailing_stop_pct": TRAILING_STOP_PCT,
        "max_drawdown_pct": MAX_DRAWDOWN_PCT,
        "min_position_eur": MIN_POSITION_EUR,
    }
    profile_cfg = get_trading_config(profile_name)

    direct_keys = (
        "max_position_pct",
        "stop_loss_pct",
        "trailing_stop_pct",
        "max_drawdown_pct",
    )
    for key in direct_keys:
        if key in profile_cfg:
            cfg[key] = float(profile_cfg[key])

    if "min_trade_eur" in profile_cfg:
        cfg["min_position_eur"] = float(profile_cfg["min_trade_eur"])
    elif "min_position_eur" in profile_cfg:
        cfg["min_position_eur"] = float(profile_cfg["min_position_eur"])

    return cfg


def max_position_eur(total_capital: float, profile_name: str | None = None) -> float:
    cfg = _risk_config(profile_name)
    return float(total_capital) * float(cfg["max_position_pct"])


def min_position_eur(profile_name: str | None = None) -> float:
    cfg = _risk_config(profile_name)
    return float(cfg["min_position_eur"])


def clamp_position_capital(capital: float, total_capital: float, profile_name: str | None = None) -> float:
    capped = min(float(capital), max_position_eur(total_capital, profile_name=profile_name))
    return max(0.0, capped)


def stop_loss_price(entry_price: float, profile_name: str | None = None) -> float:
    cfg = _risk_config(profile_name)
    return float(entry_price) * (1.0 - float(cfg["stop_loss_pct"]))


def trailing_stop_price(highest_price: float, profile_name: str | None = None) -> float:
    cfg = _risk_config(profile_name)
    return float(highest_price) * (1.0 - float(cfg["trailing_stop_pct"]))


def compute_drawdown_state(
    current_equity: float,
    peak_equity: float | None = None,
    profile_name: str | None = None,
) -> DrawdownState:
    current_equity = float(current_equity)
    cfg = _risk_config(profile_name)

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
        trading_blocked=drawdown_pct >= float(cfg["max_drawdown_pct"]),
    )


def may_open_new_positions(
    current_equity: float,
    peak_equity: float | None = None,
    profile_name: str | None = None,
) -> tuple[bool, DrawdownState]:
    state = compute_drawdown_state(
        current_equity=current_equity,
        peak_equity=peak_equity,
        profile_name=profile_name,
    )
    return (not state.trading_blocked), state


def risk_summary(profile_name: str | None = None) -> dict:
    return _risk_config(profile_name)
