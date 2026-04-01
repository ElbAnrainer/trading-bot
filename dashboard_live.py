from __future__ import annotations

import os
import select
import sys
import termios
import time
import tty
from typing import Any

from config import get_active_profile_name, get_trading_config
from dashboard import build_dashboard_data


REFRESH_SECONDS = 2.0

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
GREY = "\033[90m"


def _terminal_width(default: int = 120) -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return default


def _line(char: str = "=") -> str:
    return char * _terminal_width()


def _clear() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _fit(text: Any, width: int) -> str:
    text = str(text)
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def _fmt_money(value: float) -> str:
    return f"{float(value):,.2f} EUR"


def _fmt_pct(value: float) -> str:
    return f"{float(value):.2f}%"


def _colorize_number(value: float, text: str) -> str:
    try:
        value = float(value)
    except Exception:
        return text

    if value > 0:
        return f"{GREEN}{text}{RESET}"
    if value < 0:
        return f"{RED}{text}{RESET}"
    return text


def _header(title: str, refreshed_at: str) -> None:
    width = _terminal_width()
    profile_name = get_active_profile_name()
    print(_line("="))
    print(f"{BOLD}{title.center(width)}{RESET}")
    print(_line("-"))
    print(
        f"{CYAN}Live-Terminal{RESET} | "
        f"Profil: {profile_name} | "
        f"Aktualisiert: {refreshed_at} | "
        f"{YELLOW}q = Quit{RESET}"
    )
    print(_line("="))


def _render_profile_info() -> None:
    profile_name = get_active_profile_name()
    cfg = get_trading_config(profile_name)

    print(f"{BOLD}AKTIVES PROFIL{RESET}")
    print(
        f"Name: {profile_name} | "
        f"Max Positionen: {cfg.get('max_positions')} | "
        f"Risk/Trade: {float(cfg.get('risk_per_trade_pct', 0.0)):.2%} | "
        f"Max Portfolio-Risk: {float(cfg.get('max_portfolio_risk_pct', 0.0)):.2%}"
    )
    print(
        f"Min Hold: {cfg.get('min_hold_bars')} | "
        f"Cooldown: {cfg.get('cooldown_bars')} | "
        f"Max Trades/Woche: {cfg.get('max_new_trades_per_week')} | "
        f"Min Edge: {float(cfg.get('min_expected_edge_pct', 0.0)):.2%}"
    )
    print(_line("-"))


def _render_systemstatus(data: dict[str, Any]) -> None:
    perf = data["performance"]
    state = data["state"]

    print(f"{BOLD}SYSTEMSTATUS{RESET}")
    print(
        f"Cash: {_fmt_money(state['cash_eur'])} | "
        f"Investiert: {_fmt_money(state['total_invested_eur'])} | "
        f"Equity: {_fmt_money(state['last_equity_eur'])}"
    )
    print(
        f"Peak: {_fmt_money(state['peak_equity_eur'])} | "
        f"Drawdown: {_fmt_pct(state['drawdown_pct'])} | "
        f"Positionen: {state['positions']}"
    )
    print(
        f"Trades: {perf['closed_trades']} | "
        f"Trefferquote: {_fmt_pct(perf['hit_rate'])} | "
        f"P/L: {_colorize_number(perf['realized_pnl'], _fmt_money(perf['realized_pnl']))}"
    )
    print(
        f"Ø Trade: {_colorize_number(perf['avg_trade_pnl'], _fmt_money(perf['avg_trade_pnl']))} | "
        f"Updated: {state.get('updated_at') or '-'}"
    )
    print(_line("-"))


def _render_top_scores(data: dict[str, Any]) -> None:
    ranking = data["performance"]["ranking"]

    print(f"{BOLD}TOP SCORES{RESET}")
    header = f"{'SYM':<6}{'BONUS':>10}{'TREFFER':>10}{'Ø P/L':>14}{'TRADES':>8}"
    print(header)
    print("-" * len(header))

    if not ranking:
        print("Keine Ranking-Daten verfügbar.")
        print(_line("-"))
        return

    for row in ranking[:8]:
        bonus_text = f"{float(row.get('bonus', 0.0)):+10.2f}"
        bonus = _colorize_number(row.get("bonus", 0.0), bonus_text)
        hit = f"{float(row.get('hit_rate', 0.0)):>9.1f}%"
        avg_pnl_text = f"{float(row.get('avg_pnl', 0.0)):>14,.2f}"
        avg_pnl = _colorize_number(row.get("avg_pnl", 0.0), avg_pnl_text)
        trades = f"{int(row.get('trades', 0)):>8}"

        print(f"{row.get('symbol', '-'):<6}{bonus}{hit}{avg_pnl}{trades}")

    print(_line("-"))


def _render_portfolio_plan(data: dict[str, Any]) -> None:
    plan = data["performance"]["portfolio_plan"]

    print(f"{BOLD}PORTFOLIO-PLAN{RESET}")
    header = f"{'SYM':<6}{'GEWICHT':>10}{'KAPITAL':>14}{'SCORE':>14}"
    print(header)
    print("-" * len(header))

    if not plan:
        print("Kein Portfolio-Plan verfügbar.")
        print(_line("-"))
        return

    for row in plan[:8]:
        print(
            f"{row.get('symbol', '-'):<6}"
            f"{float(row.get('weight', 0.0)):>10.2f}"
            f"{float(row.get('capital', 0.0)):>14.2f} EUR"
            f"{float(row.get('learned_score', 0.0)):>14.2f}"
        )

    print(_line("-"))


def _render_open_positions(data: dict[str, Any]) -> None:
    positions = data["state"]["open_positions"]

    print(f"{BOLD}OFFENE POSITIONEN{RESET}")
    header = f"{'SYM':<8}{'ENTRY':>12}{'CURRENT':>12}{'SHARES':>12}{'INVESTED':>14}"
    print(header)
    print("-" * len(header))

    if not positions:
        print("Keine offenen Positionen.")
        print(_line("-"))
        return

    for sym, pos in positions.items():
        entry = float(pos.get("entry_price", 0.0))
        current = float(pos.get("current_price", 0.0))
        shares = float(pos.get("shares", 0.0))
        invested = float(pos.get("invested_eur", 0.0))

        print(
            f"{sym:<8}"
            f"{entry:>12.2f}"
            f"{current:>12.2f}"
            f"{shares:>12.4f}"
            f"{invested:>14.2f}"
        )

    print(_line("-"))


def _render_last_events(data: dict[str, Any]) -> None:
    history = data["state"]["history_tail"]

    print(f"{BOLD}LETZTE EVENTS{RESET}")
    header = f"{'ZEIT':<20}{'TYP':<8}{'SYM':<8}{'PREIS':>12}{'INFO':>22}"
    print(header)
    print("-" * len(header))

    if not history:
        print("Keine Events vorhanden.")
        print(_line("="))
        return

    for item in history[-8:]:
        price = item.get("price")
        price_str = f"{float(price):.2f}" if price is not None else "-"
        info = item.get("reason")
        if info is None and "pnl_eur" in item:
            info = f"P/L {float(item.get('pnl_eur', 0.0)):.2f} EUR"

        print(
            f"{_fit(item.get('time', '-'), 20):<20}"
            f"{_fit(item.get('type', '-'), 8):<8}"
            f"{_fit(item.get('symbol', '-'), 8):<8}"
            f"{price_str:>12}"
            f"{_fit(str(info or '-'), 22):>22}"
        )

    print(_line("="))


def render_live_terminal_once() -> None:
    data = build_dashboard_data()
    refreshed_at = time.strftime("%Y-%m-%d %H:%M:%S")

    _clear()
    _header(" MINI TRADING LIVE TERMINAL ", refreshed_at)
    _render_profile_info()
    _render_systemstatus(data)
    _render_top_scores(data)
    _render_portfolio_plan(data)
    _render_open_positions(data)
    _render_last_events(data)


def _read_key_nonblocking(timeout: float = 0.1) -> str | None:
    fd = sys.stdin.fileno()
    ready, _, _ = select.select([fd], [], [], timeout)
    if ready:
        return sys.stdin.read(1)
    return None


def run_live_terminal(refresh_seconds: float = REFRESH_SECONDS) -> None:
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setcbreak(fd)
        last_refresh = 0.0

        while True:
            now = time.time()
            if now - last_refresh >= refresh_seconds:
                render_live_terminal_once()
                last_refresh = now

            key = _read_key_nonblocking(timeout=0.1)
            if key in ("q", "Q"):
                _clear()
                print("Live-Terminal beendet.")
                return

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


if __name__ == "__main__":
    run_live_terminal()
