import sys

from config import DEFAULT_MIN_VOLUME, DEFAULT_TOP_N, PERIOD


PERIOD_MAPPING = {
    "1t": "1d",
    "1w": "5d",
    "1m": "1mo",
    "3m": "3mo",
    "6m": "6mo",
    "1j": "1y",
    "2j": "2y",
    "3j": "3y",
    "1d": "1d",
    "5d": "5d",
    "1mo": "1mo",
    "3mo": "3mo",
    "6mo": "6mo",
    "1y": "1y",
    "2y": "2y",
    "3y": "3y",
}


def normalize_period_input(user_input: str | None) -> str:
    user_input = (user_input or "").strip().lower()
    if user_input == "":
        return PERIOD
    return PERIOD_MAPPING.get(user_input, user_input)


def choose_interval(period: str) -> str:
    if period in ("1d", "5d", "1mo"):
        return "5m"
    if period in ("3mo", "6mo"):
        return "1h"
    if period in ("1y", "2y", "3y", "5y", "max"):
        return "1d"
    return "1d"


def ask_period() -> str:
    print("\nZeitraum wählen:")
    print("  1t  = 1 Tag")
    print("  1w  = 1 Woche")
    print("  1m  = 1 Monat")
    print("  3m  = 3 Monate")
    print("  6m  = 6 Monate")
    print("  1j  = 1 Jahr")
    print("  2j  = 2 Jahre")
    print("  3j  = 3 Jahre")
    print()

    return normalize_period_input(input("-> ").strip().lower())


def parse_args():
    args = sys.argv[1:]

    long_mode = "-l" in args
    top_n = DEFAULT_TOP_N
    min_volume = DEFAULT_MIN_VOLUME
    period_override = None

    i = 0
    while i < len(args):
        if args[i] == "--top" and i + 1 < len(args):
            top_n = int(args[i + 1])
            i += 2
            continue
        if args[i] == "--min-volume" and i + 1 < len(args):
            min_volume = float(args[i + 1])
            i += 2
            continue
        if args[i] == "--period" and i + 1 < len(args):
            period_override = normalize_period_input(args[i + 1])
            i += 2
            continue
        i += 1

    return long_mode, top_n, min_volume, period_override
