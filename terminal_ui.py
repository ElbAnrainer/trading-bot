from __future__ import annotations

import curses
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from config import (
    get_active_profile_name,
    get_trading_config,
    list_profile_names,
    set_active_profile_name,
)
from github_actions_control import get_auto_run_status, toggle_auto_run

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_BIN = PROJECT_ROOT / ".venv" / "bin" / "python"

CURRENT_PERIOD = "1mo"
CURRENT_TOP = 5
CURRENT_MIN_VOLUME = 1_000_000
CURRENT_CAPITAL = 1000.0

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_RED = "\033[91m"
ANSI_GREEN = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_CYAN = "\033[96m"
ANSI_GREY = "\033[90m"


# =========================================================
# Legacy-/Hilfsfunktionen für bestehende Module
# =========================================================

def colorize(text: str, color: str | None = None, bold: bool = False) -> str:
    color_map = {
        "red": ANSI_RED,
        "green": ANSI_GREEN,
        "yellow": ANSI_YELLOW,
        "cyan": ANSI_CYAN,
        "grey": ANSI_GREY,
        "gray": ANSI_GREY,
    }

    prefix = ""
    if bold:
        prefix += ANSI_BOLD
    if color and color in color_map:
        prefix += color_map[color]

    if not prefix:
        return str(text)
    return f"{prefix}{text}{ANSI_RESET}"


def get_width(default: int = 100) -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return default


def clear() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def box(title: str, lines: list[str] | tuple[str, ...] | None = None, width: int = 100) -> str:
    lines = list(lines or [])
    if lines:
        width = max(width, len(title) + 6, *(len(str(line)) + 4 for line in lines))
    else:
        width = max(width, len(title) + 6)

    top = "=" * width
    out = [top, f" {title}", top]
    out.extend(str(line) for line in lines)
    out.append(top)
    return "\n".join(out)


# =========================================================
# Pro UI
# =========================================================

MENU_ITEMS = [
    ("Standard", "run_standard"),
    ("Pro Schnell", "run_pro_fast"),
    ("Live", "run_live"),
    ("Dashboard", "run_dashboard"),
    ("Berichte aktualisieren", "refresh_reports"),
    ("Auto-Run umschalten", "toggle_auto_run"),
    ("Profil umschalten", "switch_profile"),
    ("Tests", "run_tests"),
    ("Exit", "exit_app"),
]


def _set_cursor_hidden() -> None:
    try:
        curses.curs_set(0)
    except curses.error:
        pass


def _python_bin() -> str:
    if PYTHON_BIN.exists():
        return str(PYTHON_BIN)
    return sys.executable


def _cmd_standard() -> list[str]:
    return [
        _python_bin(),
        "main.py",
        "-p",
        CURRENT_PERIOD,
        "-t",
        str(CURRENT_TOP),
        "-mv",
        str(CURRENT_MIN_VOLUME),
    ]


def _cmd_pro_fast() -> list[str]:
    return [
        _python_bin(),
        "main.py",
        "--pro",
        "--fast",
        "-p",
        CURRENT_PERIOD,
        "-t",
        str(CURRENT_TOP),
        "-mv",
        str(CURRENT_MIN_VOLUME),
    ]


def _cmd_live() -> list[str]:
    return [_python_bin(), "main.py", "--live"]


def _cmd_dashboard() -> list[str]:
    return [_python_bin(), "main.py", "--dashboard"]


def _cmd_refresh_reports() -> list[str]:
    return [_python_bin(), "refresh_reports.py"]


def _cmd_tests() -> list[str]:
    pytest_bin = PROJECT_ROOT / ".venv" / "bin" / "pytest"
    if pytest_bin.exists():
        return [str(pytest_bin), "-q"]
    return [_python_bin(), "-m", "pytest", "-q"]


def _menu_items(auto_run_status: dict[str, object] | None = None) -> list[tuple[str, str]]:
    status = auto_run_status or {"enabled": None, "label": "UNBEKANNT"}
    enabled = status.get("enabled")
    label = "Auto-Run umschalten"
    if enabled is True:
        label = "Auto-Run ausschalten"
    elif enabled is False:
        label = "Auto-Run einschalten"

    items = []
    for item_label, action in MENU_ITEMS:
        if action == "toggle_auto_run":
            items.append((label, action))
        else:
            items.append((item_label, action))
    return items


def _safe_addstr(stdscr, y: int, x: int, text: str, attr: int = 0) -> None:
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h:
        return
    if x < 0:
        text = text[-x:]
        x = 0
    if x >= w:
        return
    if not text:
        return

    max_len = max(0, w - x - 1)
    if max_len <= 0:
        return

    try:
        stdscr.addnstr(y, x, text, max_len, attr)
    except curses.error:
        pass


def _draw_box(stdscr, y: int, x: int, h: int, w: int, title: str | None = None) -> None:
    term_h, term_w = stdscr.getmaxyx()

    if h < 3 or w < 4:
        return
    if y >= term_h or x >= term_w:
        return

    max_h = max(0, term_h - y - 1)
    max_w = max(0, term_w - x - 1)

    h = min(h, max_h)
    w = min(w, max_w)

    if h < 3 or w < 4:
        return

    top = "+" + "-" * (w - 2) + "+"
    bottom = "+" + "-" * (w - 2) + "+"

    _safe_addstr(stdscr, y, x, top, curses.A_DIM)
    for row in range(y + 1, y + h - 1):
        _safe_addstr(stdscr, row, x, "|", curses.A_DIM)
        _safe_addstr(stdscr, row, x + w - 1, "|", curses.A_DIM)
    _safe_addstr(stdscr, y + h - 1, x, bottom, curses.A_DIM)

    if title:
        label = f" {title} "
        if len(label) < w - 4:
            _safe_addstr(stdscr, y, x + 2, label, curses.A_BOLD)


def _kill_process_tree(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass

    time.sleep(0.4)

    if proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def _stream_process(stdscr, title: str, cmd: list[str]) -> None:
    stdscr.clear()
    _set_cursor_hidden()
    stdscr.keypad(True)
    stdscr.nodelay(False)
    stdscr.timeout(100)

    proc = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )

    lines: list[str] = []
    scroll_offset = 0

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        _draw_box(stdscr, 0, 0, h, w, f"{title} | q = Quit | PgUp/PgDn = Scroll")
        _safe_addstr(stdscr, 1, 2, " ".join(cmd), curses.A_DIM)

        if proc.stdout is not None:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                lines.append(line.rstrip("\n"))

        view_top = 3
        view_height = max(1, h - 6)
        max_scroll = max(0, len(lines) - view_height)
        scroll_offset = min(scroll_offset, max_scroll)
        visible = lines[scroll_offset: scroll_offset + view_height]

        for i, line in enumerate(visible):
            _safe_addstr(stdscr, view_top + i, 2, line)

        status = "RUNNING" if proc.poll() is None else f"EXIT {proc.returncode}"
        _safe_addstr(stdscr, h - 2, 2, f"Status: {status}", curses.A_BOLD)

        stdscr.refresh()
        key = stdscr.getch()

        if key in (ord("q"), ord("Q")):
            _kill_process_tree(proc)
            return
        elif key == curses.KEY_NPAGE:
            scroll_offset = min(max_scroll, scroll_offset + max(1, view_height // 2))
        elif key == curses.KEY_PPAGE:
            scroll_offset = max(0, scroll_offset - max(1, view_height // 2))
        elif key in (curses.KEY_DOWN, ord("j"), 66):
            scroll_offset = min(max_scroll, scroll_offset + 1)
        elif key in (curses.KEY_UP, ord("k"), 65):
            scroll_offset = max(0, scroll_offset - 1)

        if proc.poll() is not None:
            if proc.stdout is not None:
                for line in proc.stdout.readlines():
                    lines.append(line.rstrip("\n"))

            stdscr.timeout(-1)
            _safe_addstr(stdscr, h - 2, 2, f"Status: EXIT {proc.returncode} | Enter = zurück", curses.A_BOLD)
            stdscr.refresh()
            while True:
                key = stdscr.getch()
                if key in (10, 13, curses.KEY_ENTER, ord("q"), ord("Q")):
                    return


def _message_box(stdscr, title: str, lines: list[str]) -> None:
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        box_w = min(max(56, max((len(line) for line in lines), default=20) + 6), max(20, w - 4))
        box_h = min(max(8, len(lines) + 5), max(6, h - 4))
        y = max(0, (h - box_h) // 2)
        x = max(0, (w - box_w) // 2)

        _draw_box(stdscr, y, x, box_h, box_w, title)
        for idx, line in enumerate(lines):
            _safe_addstr(stdscr, y + 2 + idx, x + 2, line)
        _safe_addstr(stdscr, y + box_h - 2, x + 2, "Enter oder q = zurück", curses.A_DIM)
        stdscr.refresh()

        key = stdscr.getch()
        if key in (10, 13, curses.KEY_ENTER, ord("q"), ord("Q"), 27):
            return


def _profile_menu(stdscr) -> None:
    profiles = list_profile_names()
    current = get_active_profile_name()
    idx = profiles.index(current) if current in profiles else 0

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        box_w = min(50, max(20, w - 4))
        box_h = min(10, max(6, h - 4))
        y = max(0, (h - box_h) // 2)
        x = max(0, (w - box_w) // 2)

        _draw_box(stdscr, y, x, box_h, box_w, "Profil umschalten")
        _safe_addstr(stdscr, y + 1, x + 2, "Enter = setzen, q = zurück", curses.A_DIM)

        for i, profile in enumerate(profiles):
            attr = curses.A_REVERSE if i == idx else 0
            marker = "*" if profile == current else " "
            _safe_addstr(stdscr, y + 3 + i, x + 3, f"{marker} {profile}", attr)

        stdscr.refresh()
        key = stdscr.getch()

        if key in (ord("q"), ord("Q"), 27):
            return
        elif key in (curses.KEY_UP, ord("k"), 65):
            idx = (idx - 1) % len(profiles)
        elif key in (curses.KEY_DOWN, ord("j"), 66):
            idx = (idx + 1) % len(profiles)
        elif key in (10, 13, curses.KEY_ENTER):
            current = set_active_profile_name(profiles[idx])


def _draw_main(stdscr, selected: int, auto_run_status: dict[str, object]) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    profile = get_active_profile_name()
    menu_items = _menu_items(auto_run_status)

    left_w = min(40, max(20, w // 2))
    right_w = max(20, w - left_w - 2)

    _draw_box(stdscr, 0, 0, h, left_w, "TRADING TERMINAL PRO")
    _draw_box(stdscr, 0, left_w + 1, h, right_w, "Status")

    _safe_addstr(stdscr, 2, 2, f"Profil      : {profile}", curses.A_BOLD)
    _safe_addstr(stdscr, 3, 2, f"Zeitraum    : {CURRENT_PERIOD}")
    _safe_addstr(stdscr, 4, 2, f"Top-N       : {CURRENT_TOP}")
    _safe_addstr(stdscr, 5, 2, f"Min-Volumen : {CURRENT_MIN_VOLUME}")
    _safe_addstr(stdscr, 6, 2, f"Kapital     : {CURRENT_CAPITAL:.2f} EUR")
    _safe_addstr(stdscr, 8, 2, "Steuerung:", curses.A_BOLD)
    _safe_addstr(stdscr, 9, 2, "↑/↓ oder j/k = bewegen")
    _safe_addstr(stdscr, 10, 2, "Enter = starten")
    _safe_addstr(stdscr, 11, 2, "q = beenden")

    menu_y = 14
    for i, (label, _) in enumerate(menu_items):
        attr = curses.A_REVERSE if i == selected else 0
        _safe_addstr(stdscr, menu_y + i, 3, label, attr)

    cfg = get_trading_config(profile)
    rx = left_w + 3
    _safe_addstr(stdscr, 2, rx, "Aktives Profil", curses.A_BOLD)
    _safe_addstr(stdscr, 4, rx, f"Risk / Trade       : {float(cfg.get('risk_per_trade_pct', 0.0)):.2%}")
    _safe_addstr(stdscr, 5, rx, f"Max Position       : {float(cfg.get('max_position_pct', 0.0)):.2%}")
    _safe_addstr(stdscr, 6, rx, f"Portfolio Risk Max : {float(cfg.get('max_portfolio_risk_pct', 0.0)):.2%}")
    _safe_addstr(stdscr, 7, rx, f"Min Hold           : {cfg.get('min_hold_bars')}")
    _safe_addstr(stdscr, 8, rx, f"Cooldown           : {cfg.get('cooldown_bars')}")
    _safe_addstr(stdscr, 9, rx, f"Max Trades/Woche   : {cfg.get('max_new_trades_per_week')}")
    _safe_addstr(stdscr, 10, rx, f"Min Edge           : {float(cfg.get('min_expected_edge_pct', 0.0)):.2%}")
    _safe_addstr(stdscr, 11, rx, f"Vol Target         : {float(cfg.get('vol_target', 0.0)):.4f}")
    _safe_addstr(stdscr, 13, rx, "GitHub Auto-Run", curses.A_BOLD)
    _safe_addstr(stdscr, 14, rx, f"Status             : {auto_run_status.get('label', 'UNBEKANNT')}")
    _safe_addstr(stdscr, 15, rx, str(auto_run_status.get("detail", "-")), curses.A_DIM)

    _safe_addstr(stdscr, h - 2, 2, "Terminal Pro UI – q = Exit", curses.A_DIM)
    stdscr.refresh()


def _show_start_screen(stdscr) -> None:
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    _draw_box(stdscr, 0, 0, h, w, "START")
    _safe_addstr(stdscr, 2, 2, "Trading Terminal Pro wird gestartet...", curses.A_BOLD)
    _safe_addstr(stdscr, 4, 2, f"TTY stdin : {sys.stdin.isatty()}")
    _safe_addstr(stdscr, 5, 2, f"TTY stdout: {sys.stdout.isatty()}")
    _safe_addstr(stdscr, 6, 2, f"TERM      : {os.environ.get('TERM', '-')}")
    _safe_addstr(stdscr, 8, 2, "Drücke Enter oder eine andere Taste für das Hauptmenü.")
    stdscr.refresh()

    stdscr.nodelay(False)
    stdscr.timeout(-1)
    stdscr.getch()


def main(stdscr) -> None:
    _set_cursor_hidden()
    stdscr.keypad(True)
    curses.noecho()
    curses.cbreak()
    stdscr.nodelay(False)
    stdscr.timeout(-1)

    selected = 0
    auto_run_status = get_auto_run_status()

    _show_start_screen(stdscr)

    while True:
        menu_items = _menu_items(auto_run_status)
        selected = min(selected, len(menu_items) - 1)
        _draw_main(stdscr, selected, auto_run_status)
        stdscr.nodelay(False)
        stdscr.timeout(-1)
        key = stdscr.getch()

        if key in (ord("q"), ord("Q")):
            return
        elif key in (curses.KEY_UP, ord("k"), 65):
            selected = (selected - 1) % len(menu_items)
        elif key in (curses.KEY_DOWN, ord("j"), 66):
            selected = (selected + 1) % len(menu_items)
        elif key in (10, 13, curses.KEY_ENTER):
            _, action = menu_items[selected]

            if action == "run_standard":
                _stream_process(stdscr, "Standard", _cmd_standard())
            elif action == "run_pro_fast":
                _stream_process(stdscr, "Pro Schnell", _cmd_pro_fast())
            elif action == "run_live":
                _stream_process(stdscr, "Live", _cmd_live())
            elif action == "run_dashboard":
                _stream_process(stdscr, "Dashboard", _cmd_dashboard())
            elif action == "refresh_reports":
                _stream_process(stdscr, "Berichte aktualisieren", _cmd_refresh_reports())
            elif action == "toggle_auto_run":
                result = toggle_auto_run()
                auto_run_status = get_auto_run_status()
                _message_box(
                    stdscr,
                    "GitHub Auto-Run",
                    [
                        result.get("message", "Kein Status verfügbar."),
                        f"Aktueller Status: {auto_run_status.get('label', 'UNBEKANNT')}",
                        str(auto_run_status.get("detail", "-")),
                    ],
                )
            elif action == "run_tests":
                _stream_process(stdscr, "Tests", _cmd_tests())
            elif action == "switch_profile":
                _profile_menu(stdscr)
            elif action == "exit_app":
                return


if __name__ == "__main__":
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Keine interaktive TTY-Umgebung erkannt.")
        raise SystemExit(1)

    curses.wrapper(main)
