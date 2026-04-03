from __future__ import annotations

import os
import re
import select
import sys
import termios
import time
import tty
from typing import Any

from config import get_active_profile_name, get_trading_config
from dashboard import build_dashboard_data
from security_identifiers import identifiers_text


REFRESH_SECONDS = 2.0
TWO_COLUMN_MIN_WIDTH = 140
COLUMN_GAP = 3

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
GREY = "\033[90m"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _terminal_width(default: int = 120) -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return default


def _line(char: str = "=", width: int | None = None) -> str:
    return char * (width or _terminal_width())


def _clear() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _strip_ansi(text: Any) -> str:
    return ANSI_RE.sub("", str(text))


def _visible_len(text: Any) -> int:
    return len(_strip_ansi(text))


def _truncate_ansi(text: Any, width: int) -> str:
    text = str(text)
    if width <= 0:
        return ""
    if _visible_len(text) <= width:
        return text
    if width == 1:
        return "."

    target = width - 1
    out: list[str] = []
    visible = 0
    idx = 0
    saw_ansi = False

    while idx < len(text) and visible < target:
        if text[idx] == "\033" and idx + 1 < len(text) and text[idx + 1] == "[":
            saw_ansi = True
            end = idx + 2
            while end < len(text) and text[end] != "m":
                end += 1
            if end < len(text):
                out.append(text[idx : end + 1])
                idx = end + 1
                continue
        out.append(text[idx])
        visible += 1
        idx += 1

    out.append("…")
    if saw_ansi:
        out.append(RESET)
    return "".join(out)


def _pad_ansi(text: Any, width: int) -> str:
    clipped = _truncate_ansi(text, width)
    return clipped + (" " * max(0, width - _visible_len(clipped)))


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


def _header_lines(title: str, refreshed_at: str, width: int, profile_name: str) -> list[str]:
    return [
        _line("=", width),
        f"{BOLD}{title.center(width)}{RESET}",
        _line("-", width),
        (
            f"{CYAN}Live-Terminal{RESET} | "
            f"Profil: {profile_name} | "
            f"Aktualisiert: {refreshed_at} | "
            f"{YELLOW}q = Quit{RESET}"
        ),
        _line("=", width),
    ]


def _box(title: str, rows: list[str], width: int) -> list[str]:
    width = max(28, width)
    inner = width - 4
    lines = [
        "+" + "-" * (width - 2) + "+",
        f"| {_pad_ansi(f'{BOLD}{title}{RESET}', inner)} |",
        "|" + "-" * (width - 2) + "|",
    ]
    lines.extend(f"| {_pad_ansi(row, inner)} |" for row in rows)
    lines.append("+" + "-" * (width - 2) + "+")
    return lines


def _profile_rows(profile_name: str, cfg: dict[str, Any]) -> list[str]:
    return [
        f"Name: {profile_name}",
        f"Max Positionen: {cfg.get('max_positions')}",
        f"Risk/Trade: {float(cfg.get('risk_per_trade_pct', 0.0)):.2%}",
        f"Max Portfolio-Risk: {float(cfg.get('max_portfolio_risk_pct', 0.0)):.2%}",
        f"Min Hold: {cfg.get('min_hold_bars')} | Cooldown: {cfg.get('cooldown_bars')}",
        (
            f"Max Trades/Woche: {cfg.get('max_new_trades_per_week')} | "
            f"Min Edge: {float(cfg.get('min_expected_edge_pct', 0.0)):.2%}"
        ),
    ]


def _systemstatus_rows(data: dict[str, Any]) -> list[str]:
    analysis = data.get("analysis", {})
    perf = data["performance"]
    state = data["state"]

    return [
        f"Cash: {_fmt_money(state['cash_eur'])}",
        f"Investiert: {_fmt_money(state['total_invested_eur'])}",
        f"Equity: {_fmt_money(state['last_equity_eur'])}",
        f"Peak: {_fmt_money(state['peak_equity_eur'])}",
        f"Drawdown: {_fmt_pct(state['drawdown_pct'])} | Positionen: {state['positions']}",
        f"Trades: {perf['closed_trades']} | Trefferquote: {_fmt_pct(perf['hit_rate'])}",
        f"P/L: {_colorize_number(perf['realized_pnl'], _fmt_money(perf['realized_pnl']))}",
        f"O Trade: {_colorize_number(perf['avg_trade_pnl'], _fmt_money(perf['avg_trade_pnl']))}",
        (
            f"Analyse: {analysis.get('period', '-')} / {analysis.get('interval', '-')} | "
            f"Ergebnisse: {len(analysis.get('current_results', []))} | "
            f"Plan: {len(analysis.get('trading_plan', []))}"
        ),
        f"Updated: {analysis.get('generated_at') or state.get('updated_at') or '-'}",
    ]


def _top_scores_rows(data: dict[str, Any]) -> list[str]:
    current_results = data.get("analysis", {}).get("current_results", [])
    ranking = data["performance"]["ranking"]

    if current_results:
        rows = [f"{'SYM':<6}{'SIG':<6}{'P/L':>12}{'TRD':>6}{'SCORE':>10}"]
        for row in current_results[:8]:
            pnl_text = f"{float(row.get('pnl_eur', 0.0)):>12,.2f}"
            pnl = _colorize_number(row.get("pnl_eur", 0.0), pnl_text)
            trades = f"{int(row.get('trade_count', 0)):>6}"
            score = f"{float(row.get('score', 0.0)):>10.2f}"
            rows.append(
                f"{_fit(row.get('symbol', '-'), 6):<6}"
                f"{_fit(row.get('signal', '-'), 6):<6}"
                f"{pnl}"
                f"{trades}"
                f"{score}"
            )
            rows.append(f"  {identifiers_text(row.get('isin'), row.get('wkn'))}")
        return rows

    rows = [f"{'SYM':<6}{'BONUS':>10}{'HIT':>8}{'O P/L':>12}{'TRD':>6}"]

    if not ranking:
        rows.append("Keine Ranking-Daten verfugbar.")
        return rows

    for row in ranking[:8]:
        bonus_text = f"{float(row.get('bonus', 0.0)):+10.2f}"
        bonus = _colorize_number(row.get("bonus", 0.0), bonus_text)
        hit = f"{float(row.get('hit_rate', 0.0)):>7.1f}%"
        avg_pnl_text = f"{float(row.get('avg_pnl', 0.0)):>12,.2f}"
        avg_pnl = _colorize_number(row.get("avg_pnl", 0.0), avg_pnl_text)
        trades = f"{int(row.get('trades', 0)):>6}"
        rows.append(f"{_fit(row.get('symbol', '-'), 6):<6}{bonus}{hit}{avg_pnl}{trades}")
        rows.append(f"  {identifiers_text(row.get('isin'), row.get('wkn'))}")

    return rows


def _portfolio_plan_rows(data: dict[str, Any]) -> list[str]:
    analysis_plan = data.get("analysis", {}).get("trading_plan", [])
    plan = analysis_plan or data["performance"]["portfolio_plan"]
    rows = [f"{'SYM':<6}{'GEW.%':>10}{'KAPITAL':>14}{'SCORE':>10}"]

    if not plan:
        rows.append("Kein Portfolio-Plan verfugbar.")
        return rows

    for row in plan[:8]:
        rows.append(
            f"{_fit(row.get('symbol', '-'), 6):<6}"
            f"{float(row.get('weight', 0.0)):>10.2f}"
            f"{float(row.get('capital', 0.0)):>14.2f}"
            f"{float(row.get('learned_score', 0.0)):>10.2f}"
        )
        rows.append(f"  {identifiers_text(row.get('isin'), row.get('wkn'))}")

    return rows


def _open_positions_rows(data: dict[str, Any]) -> list[str]:
    positions = data["state"]["open_positions"]
    rows = [f"{'SYM':<7}{'ENTRY':>10}{'CURR':>10}{'SHARES':>10}{'INV':>11}"]

    if not positions:
        rows.append("Keine offenen Positionen.")
        return rows

    for sym, pos in positions.items():
        entry = float(pos.get("entry_price", 0.0))
        current = float(pos.get("current_price", 0.0))
        shares = float(pos.get("shares", 0.0))
        invested = float(pos.get("invested_eur", 0.0))

        rows.append(
            f"{_fit(sym, 7):<7}"
            f"{entry:>10.2f}"
            f"{current:>10.2f}"
            f"{shares:>10.3f}"
            f"{invested:>11.2f}"
        )
        rows.append(f"  {identifiers_text(pos.get('isin'), pos.get('wkn'))}")

    return rows


def _last_events_rows(data: dict[str, Any], content_width: int) -> list[str]:
    history = data["state"]["history_tail"]

    time_w = 14 if content_width < 66 else 16
    type_w = 6
    sym_w = 6
    price_w = 9
    info_w = max(10, content_width - time_w - type_w - sym_w - price_w)

    rows = [f"{'ZEIT':<{time_w}}{'TYP':<{type_w}}{'SYM':<{sym_w}}{'PREIS':>{price_w}}{'INFO':>{info_w}}"]

    if not history:
        rows.append("Keine Events vorhanden.")
        return rows

    for item in history[-8:]:
        price = item.get("price")
        price_str = f"{float(price):.2f}" if price is not None else "-"
        info = item.get("reason")
        if info is None and "pnl_eur" in item:
            info = f"P/L {float(item.get('pnl_eur', 0.0)):.2f} EUR"

        rows.append(
            f"{_fit(item.get('time', '-'), time_w):<{time_w}}"
            f"{_fit(item.get('type', '-'), type_w):<{type_w}}"
            f"{_fit(item.get('symbol', '-'), sym_w):<{sym_w}}"
            f"{_fit(price_str, price_w):>{price_w}}"
            f"{_fit(str(info or '-'), info_w):>{info_w}}"
        )
        rows.append(f"  {identifiers_text(item.get('isin'), item.get('wkn'))}")

    return rows


def _stack_boxes(boxes: list[list[str]]) -> list[str]:
    lines: list[str] = []
    for idx, box in enumerate(boxes):
        if idx:
            lines.append("")
        lines.extend(box)
    return lines


def _merge_columns(left_lines: list[str], right_lines: list[str], left_width: int, right_width: int) -> list[str]:
    merged: list[str] = []
    max_lines = max(len(left_lines), len(right_lines))

    for idx in range(max_lines):
        left = left_lines[idx] if idx < len(left_lines) else ""
        right = right_lines[idx] if idx < len(right_lines) else ""
        merged.append(f"{_pad_ansi(left, left_width)}{' ' * COLUMN_GAP}{_pad_ansi(right, right_width)}")

    return merged


def _build_live_terminal_lines(data: dict[str, Any], refreshed_at: str, width: int | None = None) -> list[str]:
    width = width or _terminal_width()
    profile_name = get_active_profile_name()
    cfg = get_trading_config(profile_name)

    lines = _header_lines(" MINI TRADING LIVE TERMINAL ", refreshed_at, width, profile_name)

    if width >= TWO_COLUMN_MIN_WIDTH:
        left_width = (width - COLUMN_GAP) // 2
        right_width = width - COLUMN_GAP - left_width

        left_boxes = [
            _box("AKTIVES PROFIL", _profile_rows(profile_name, cfg), left_width),
            _box("SYSTEMSTATUS", _systemstatus_rows(data), left_width),
            _box("TOP SCORES", _top_scores_rows(data), left_width),
        ]
        right_boxes = [
            _box("PORTFOLIO-PLAN", _portfolio_plan_rows(data), right_width),
            _box("OFFENE POSITIONEN", _open_positions_rows(data), right_width),
            _box("LETZTE EVENTS", _last_events_rows(data, right_width - 4), right_width),
        ]
        lines.extend(_merge_columns(_stack_boxes(left_boxes), _stack_boxes(right_boxes), left_width, right_width))
        return lines

    stacked_boxes = [
        _box("AKTIVES PROFIL", _profile_rows(profile_name, cfg), width),
        _box("SYSTEMSTATUS", _systemstatus_rows(data), width),
        _box("TOP SCORES", _top_scores_rows(data), width),
        _box("PORTFOLIO-PLAN", _portfolio_plan_rows(data), width),
        _box("OFFENE POSITIONEN", _open_positions_rows(data), width),
        _box("LETZTE EVENTS", _last_events_rows(data, width - 4), width),
    ]

    for idx, box in enumerate(stacked_boxes):
        if idx:
            lines.append("")
        lines.extend(box)

    return lines


def render_live_terminal_once() -> None:
    data = build_dashboard_data()
    refreshed_at = time.strftime("%Y-%m-%d %H:%M:%S")

    _clear()
    for line in _build_live_terminal_lines(data, refreshed_at):
        print(line)


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
