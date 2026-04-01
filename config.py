from __future__ import annotations

import os


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = "reports"
REPORTS_PATH = os.path.join(PROJECT_ROOT, REPORTS_DIR)

LOGS_DIR = os.path.join(REPORTS_DIR, "logs")
STATUS_DIR = os.path.join(REPORTS_DIR, "status")

TRADING_JOURNAL_CSV = os.path.join(REPORTS_DIR, "trading_journal.csv")
LEARNED_SCORES_JSON = os.path.join(REPORTS_DIR, "learned_scores.json")
PORTFOLIO_STATE_JSON = os.path.join(REPORTS_DIR, "portfolio_state.json")
REALISTIC_BACKTEST_JSON = os.path.join(REPORTS_DIR, "realistic_backtest_latest.json")
DASHBOARD_JSON = os.path.join(REPORTS_DIR, "dashboard_latest.json")
DASHBOARD_HTML = os.path.join(REPORTS_DIR, "dashboard_latest.html")
TRADING_REPORT_PDF = os.path.join(REPORTS_DIR, "trading_report_latest.pdf")
DAILY_REPORT_HTML = os.path.join(REPORTS_DIR, "daily_report_latest.html")
DAILY_REPORT_TXT = os.path.join(REPORTS_DIR, "daily_report_latest.txt")
DAILY_REPORT_CSV = os.path.join(REPORTS_DIR, "daily_report_latest.csv")
DAILY_REPORT_XML = os.path.join(REPORTS_DIR, "daily_report_latest.xml")
DAILY_REPORT_PDF = os.path.join(REPORTS_DIR, "daily_report_latest.pdf")

BASE_CURRENCY = "EUR"

PERIOD = "1mo"
DEFAULT_TOP_N = 5
DEFAULT_MIN_VOLUME = 1_000_000
RECOMMENDATION_TOP_N = DEFAULT_TOP_N

BENCHMARK_SYMBOL = "^GSPC"

SLIPPAGE_PCT = 0.0005
FX_FEE_PCT = 0.0025
BROKER_FEE_NATIVE = 1.00

FX_SYMBOL = {
    "USD": "EURUSD=X",
    "GBP": "EURGBP=X",
    "CHF": "EURCHF=X",
    "JPY": "EURJPY=X",
    "CAD": "EURCAD=X",
}

FX_FALLBACK_RATES_TO_EUR = {
    "EUR": 1.0,
    "USD": 0.92,
    "GBP": 1.17,
    "CHF": 1.04,
    "JPY": 0.0062,
    "CAD": 0.68,
}

UNIVERSE_SOURCES = [
    "sp500",
    "nasdaq100",
    "dowjones",
]

INITIAL_CAPITAL = 10_000.0
INITIAL_CASH_EUR = 10_000.0
MAX_POSITIONS = 5
STOP_LOSS_PCT = 0.08
TRAILING_STOP_PCT = 0.10
MIN_TRADE_EUR = 250.0

TRADING_PROFILES = {
    "konservativ": {
        "initial_capital": 10_000.0,
        "max_positions": 4,
        "fee_pct": 0.0010,
        "slippage_pct": 0.0005,
        "stop_loss_pct": 0.08,
        "trailing_stop_pct": 0.10,
        "min_trade_eur": 400.0,
        "min_hold_bars": 7,
        "cooldown_bars": 7,
        "max_new_trades_per_bar": 1,
        "max_new_trades_per_week": 2,
        "min_learned_score": 10.0,
        "max_volatility_20": 0.035,
        "min_stop_distance_pct": 0.05,
        "min_expected_edge_pct": 0.020,
        "min_hold_days": 7,
        "cooldown_days": 7,
        "max_new_trades_per_run": 1,
        "risk_per_trade_pct": 0.0075,
        "max_position_pct": 0.20,
        "max_portfolio_risk_pct": 0.025,
        "vol_target": 0.025,
        "adaptive_stop_min_pct": 0.05,
        "adaptive_stop_max_pct": 0.10,
        "adaptive_trailing_min_pct": 0.07,
        "adaptive_trailing_max_pct": 0.12,
    },
    "mittel": {
        "initial_capital": 10_000.0,
        "max_positions": 5,
        "fee_pct": 0.0010,
        "slippage_pct": 0.0005,
        "stop_loss_pct": 0.08,
        "trailing_stop_pct": 0.10,
        "min_trade_eur": 250.0,
        "min_hold_bars": 5,
        "cooldown_bars": 5,
        "max_new_trades_per_bar": 1,
        "max_new_trades_per_week": 3,
        "min_learned_score": 0.0,
        "max_volatility_20": 0.045,
        "min_stop_distance_pct": 0.04,
        "min_expected_edge_pct": 0.015,
        "min_hold_days": 5,
        "cooldown_days": 5,
        "max_new_trades_per_run": 1,
        "risk_per_trade_pct": 0.0100,
        "max_position_pct": 0.25,
        "max_portfolio_risk_pct": 0.040,
        "vol_target": 0.035,
        "adaptive_stop_min_pct": 0.05,
        "adaptive_stop_max_pct": 0.12,
        "adaptive_trailing_min_pct": 0.07,
        "adaptive_trailing_max_pct": 0.14,
    },
    "offensiv": {
        "initial_capital": 10_000.0,
        "max_positions": 6,
        "fee_pct": 0.0010,
        "slippage_pct": 0.0005,
        "stop_loss_pct": 0.07,
        "trailing_stop_pct": 0.09,
        "min_trade_eur": 200.0,
        "min_hold_bars": 3,
        "cooldown_bars": 3,
        "max_new_trades_per_bar": 2,
        "max_new_trades_per_week": 5,
        "min_learned_score": -20.0,
        "max_volatility_20": 0.060,
        "min_stop_distance_pct": 0.03,
        "min_expected_edge_pct": 0.010,
        "min_hold_days": 3,
        "cooldown_days": 3,
        "max_new_trades_per_run": 2,
        "risk_per_trade_pct": 0.0150,
        "max_position_pct": 0.30,
        "max_portfolio_risk_pct": 0.060,
        "vol_target": 0.050,
        "adaptive_stop_min_pct": 0.04,
        "adaptive_stop_max_pct": 0.14,
        "adaptive_trailing_min_pct": 0.06,
        "adaptive_trailing_max_pct": 0.16,
    },
}

DEFAULT_PROFILE_NAME = "mittel"
_PROFILE_FILE = os.path.join(REPORTS_DIR, "active_profile.txt")


def _ensure_reports_dir() -> None:
    os.makedirs(REPORTS_DIR, exist_ok=True)


def list_profile_names() -> list[str]:
    return list(TRADING_PROFILES.keys())


def _normalize_profile_name(profile_name: str | None) -> str:
    if not profile_name:
        return DEFAULT_PROFILE_NAME
    name = str(profile_name).strip().lower()
    if name not in TRADING_PROFILES:
        available = ", ".join(sorted(TRADING_PROFILES))
        raise ValueError(f"Unbekanntes Profil: {name}. Verfügbar: {available}")
    return name


def get_active_profile_name() -> str:
    try:
        if os.path.exists(_PROFILE_FILE):
            value = open(_PROFILE_FILE, "r", encoding="utf-8").read().strip().lower()
            if value in TRADING_PROFILES:
                return value
    except Exception:
        pass
    return DEFAULT_PROFILE_NAME


def set_active_profile_name(profile_name: str) -> str:
    name = _normalize_profile_name(profile_name)
    _ensure_reports_dir()
    with open(_PROFILE_FILE, "w", encoding="utf-8") as f:
        f.write(name)
    return name


def get_trading_config(profile_name: str | None = None) -> dict:
    name = _normalize_profile_name(profile_name or get_active_profile_name())
    return dict(TRADING_PROFILES[name])


_active = get_trading_config()

PROFILE_INITIAL_CAPITAL = float(_active["initial_capital"])
PROFILE_MAX_POSITIONS = int(_active["max_positions"])
PROFILE_FEE_PCT = float(_active["fee_pct"])
PROFILE_SLIPPAGE_PCT = float(_active["slippage_pct"])
PROFILE_STOP_LOSS_PCT = float(_active["stop_loss_pct"])
PROFILE_TRAILING_STOP_PCT = float(_active["trailing_stop_pct"])
PROFILE_MIN_TRADE_EUR = float(_active["min_trade_eur"])

PROFILE_MIN_HOLD_BARS = int(_active["min_hold_bars"])
PROFILE_COOLDOWN_BARS = int(_active["cooldown_bars"])
PROFILE_MAX_NEW_TRADES_PER_BAR = int(_active["max_new_trades_per_bar"])
PROFILE_MAX_NEW_TRADES_PER_WEEK = int(_active["max_new_trades_per_week"])
PROFILE_MIN_LEARNED_SCORE = float(_active["min_learned_score"])
PROFILE_MAX_VOLATILITY_20 = float(_active["max_volatility_20"])
PROFILE_MIN_STOP_DISTANCE_PCT = float(_active["min_stop_distance_pct"])
PROFILE_MIN_EXPECTED_EDGE_PCT = float(_active["min_expected_edge_pct"])

PROFILE_MIN_HOLD_DAYS = int(_active["min_hold_days"])
PROFILE_COOLDOWN_DAYS = int(_active["cooldown_days"])
PROFILE_MAX_NEW_TRADES_PER_RUN = int(_active["max_new_trades_per_run"])

INITIAL_CAPITAL_EUR = PROFILE_INITIAL_CAPITAL
INITIAL_CASH = PROFILE_INITIAL_CAPITAL
INITIAL_CASH_EUR = PROFILE_INITIAL_CAPITAL

MAX_OPEN_POSITIONS = PROFILE_MAX_POSITIONS

FEE_PCT = PROFILE_FEE_PCT
BROKER_FEE_PCT = PROFILE_FEE_PCT

MIN_HOLDING_BARS = PROFILE_MIN_HOLD_BARS
MIN_HOLD_BARS = PROFILE_MIN_HOLD_BARS

COOLDOWN_BARS = PROFILE_COOLDOWN_BARS
COOLDOWN_AFTER_EXIT_BARS = PROFILE_COOLDOWN_BARS

MAX_TRADES_PER_BAR = PROFILE_MAX_NEW_TRADES_PER_BAR
MAX_NEW_TRADES_PER_BAR = PROFILE_MAX_NEW_TRADES_PER_BAR

MAX_TRADES_PER_WEEK = PROFILE_MAX_NEW_TRADES_PER_WEEK
MAX_NEW_TRADES_PER_WEEK = PROFILE_MAX_NEW_TRADES_PER_WEEK

MIN_SCORE_FOR_ENTRY = PROFILE_MIN_LEARNED_SCORE
MIN_LEARNED_SCORE = PROFILE_MIN_LEARNED_SCORE

MAX_ALLOWED_VOLATILITY_20 = PROFILE_MAX_VOLATILITY_20
MAX_VOLATILITY_20 = PROFILE_MAX_VOLATILITY_20

MIN_STOP_DISTANCE = PROFILE_MIN_STOP_DISTANCE_PCT
MIN_STOP_DISTANCE_PCT = PROFILE_MIN_STOP_DISTANCE_PCT

MIN_EXPECTED_EDGE = PROFILE_MIN_EXPECTED_EDGE_PCT
MIN_EXPECTED_EDGE_PCT = PROFILE_MIN_EXPECTED_EDGE_PCT

MIN_HOLD_DAYS = PROFILE_MIN_HOLD_DAYS
COOLDOWN_DAYS = PROFILE_COOLDOWN_DAYS
MAX_NEW_TRADES_PER_RUN = PROFILE_MAX_NEW_TRADES_PER_RUN
