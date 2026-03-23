# Dynamisches Universum:
# Die Ticker werden online aus aktuellen Index-Mitgliederlisten geladen.
UNIVERSE_SOURCES = [
    "sp500",
    "nasdaq100",
]

# Benchmark für relative Stärke
BENCHMARK_SYMBOL = "SPY"

# Anzeige / Basiswährung
BASE_CURRENCY = "EUR"
FX_SYMBOL = "EURUSD=X"

INTERVAL = "5m"
PERIOD = "1mo"

# Portfolio-Basis in EUR
INITIAL_CASH_EUR = 10000.0

# Kosten
BROKER_FEE_NATIVE = 1.0
SLIPPAGE_PCT = 0.0005
FX_FEE_PCT = 0.0025

# Risiko / Money Management
RISK_PER_TRADE_PCT = 0.01
MAX_ALLOC_PCT = 0.20
STOP_LOSS_PCT = 0.03
TAKE_PROFIT_PCT = 0.06

# Strategie
EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14
RSI_BUY_MIN = 55
RSI_BUY_MAX = 75
RSI_SELL_MIN = 45
TREND_SMA = 200
BREAKOUT_LOOKBACK = 20
ATR_PERIOD = 14
MIN_ATR_PCT = 1.0
COOLDOWN_BARS = 5

# Relative Stärke
RELATIVE_STRENGTH_LOOKBACK = 20
MIN_RELATIVE_STRENGTH_PCT = 2.0

STATE_FILE = "state.json"
BROKER_FILE = "broker_state.json"

# CLI Defaults
DEFAULT_TOP_N = 3
DEFAULT_MIN_VOLUME = 5_000_000

# Reports
REPORTS_DIR = "reports"

# Zukunftsempfehlung / Beobachtungsliste
RECOMMENDATION_TOP_N = 5
MIN_SCORE_FOR_BUY = 40
MIN_SCORE_FOR_WATCH = 22

# Fallbacks, falls FX-Daten temporär fehlen
FX_FALLBACK_RATES_TO_EUR = {
    "EUR": 1.0,
    "USD": 0.92,
    "GBP": 1.17,
    "CHF": 1.04,
    "JPY": 0.0062,
    "CAD": 0.68,
    "AUD": 0.61,
}
