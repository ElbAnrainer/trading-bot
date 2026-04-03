#!/usr/bin/env bash

set -u

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT" || exit 1

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

PYTHON_BIN="python"
[ -x ".venv/bin/python" ] && PYTHON_BIN=".venv/bin/python"

export PYTHONPATH="$PROJECT_ROOT"

CURRENT_PERIOD="1mo"
CURRENT_TOP="5"
CURRENT_MIN_VOLUME="1000000"

ACTIVE_CHILD_PID=""
ACTIVE_PGID=""
WATCHER_PID=""
STATUS_PID=""
PROCESS_STATE="idle"

RESET="\033[0m"
BOLD="\033[1m"
DIM="\033[2m"
RED="\033[91m"
GREEN="\033[92m"
YELLOW="\033[93m"
BLUE="\033[94m"
CYAN="\033[96m"
GREY="\033[90m"
WHITE="\033[97m"

line() {
  printf "${GREY}====================================================${RESET}\n"
}

header() {
  clear
  line
  printf "${BOLD}${CYAN}%s${RESET}\n" "$1"
  line
  printf "${WHITE}Zeitraum:${RESET} %s | ${WHITE}Top-N:${RESET} %s | ${WHITE}Min-Volumen:${RESET} %s\n" \
    "$CURRENT_PERIOD" "$CURRENT_TOP" "$CURRENT_MIN_VOLUME"
  printf "${WHITE}Hotkeys:${RESET} ${YELLOW}q${RESET}=Quit | ${YELLOW}p${RESET}=Pause/Resume | ${YELLOW}r${RESET}=Restart | ${YELLOW}s${RESET}=Status\n"
  line
  echo
}

pause_prompt() {
  echo
  read -r -p "Enter..."
}

green_msg() { printf "${GREEN}%s${RESET}\n" "$1"; }
red_msg() { printf "${RED}%s${RESET}\n" "$1"; }
yellow_msg() { printf "${YELLOW}%s${RESET}\n" "$1"; }
blue_msg() { printf "${BLUE}%s${RESET}\n" "$1"; }

get_pgid() {
  local pid="$1"
  ps -o pgid= "$pid" 2>/dev/null | tr -d ' '
}

is_running() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

stop_process_group() {
  local pgid="$1"
  [ -z "${pgid:-}" ] && return 0
  kill -TERM "-$pgid" 2>/dev/null || true
  sleep 0.4
  kill -KILL "-$pgid" 2>/dev/null || true
}

toggle_pause_process_group() {
  local pgid="$1"
  [ -z "${pgid:-}" ] && return 0

  if [ "$PROCESS_STATE" = "paused" ]; then
    kill -CONT "-$pgid" 2>/dev/null || true
    PROCESS_STATE="running"
    echo
    green_msg ">>> fortgesetzt"
  else
    kill -STOP "-$pgid" 2>/dev/null || true
    PROCESS_STATE="paused"
    echo
    yellow_msg ">>> pausiert"
  fi
}

cleanup_background_helpers() {
  if [ -n "${WATCHER_PID:-}" ]; then
    kill "$WATCHER_PID" 2>/dev/null || true
    wait "$WATCHER_PID" 2>/dev/null || true
    WATCHER_PID=""
  fi

  if [ -n "${STATUS_PID:-}" ]; then
    kill "$STATUS_PID" 2>/dev/null || true
    wait "$STATUS_PID" 2>/dev/null || true
    STATUS_PID=""
  fi
}

status_color() {
  case "$1" in
    running) printf "%b" "$GREEN" ;;
    paused)  printf "%b" "$YELLOW" ;;
    idle)    printf "%b" "$GREY" ;;
    *)       printf "%b" "$CYAN" ;;
  esac
}

print_runtime_status() {
  if [ -z "${ACTIVE_CHILD_PID:-}" ] || [ -z "${ACTIVE_PGID:-}" ]; then
    return
  fi

  if ! is_running "$ACTIVE_CHILD_PID"; then
    return
  fi

  local elapsed rss cpu state_col
  elapsed="$(ps -o etime= -p "$ACTIVE_CHILD_PID" 2>/dev/null | xargs)"
  rss="$(ps -o rss= -p "$ACTIVE_CHILD_PID" 2>/dev/null | xargs)"
  cpu="$(ps -o %cpu= -p "$ACTIVE_CHILD_PID" 2>/dev/null | xargs)"
  state_col="$(status_color "$PROCESS_STATE")"

  [ -z "$elapsed" ] && elapsed="-"
  [ -z "$rss" ] && rss="-"
  [ -z "$cpu" ] && cpu="-"

  printf "\r${CYAN}[STATUS]${RESET} pid=${WHITE}%s${RESET} pgid=${WHITE}%s${RESET} state=%b%s${RESET} runtime=${WHITE}%s${RESET} cpu=${WHITE}%s%%${RESET} rss=${WHITE}%sKB${RESET}      " \
    "$ACTIVE_CHILD_PID" "$ACTIVE_PGID" "$state_col" "$PROCESS_STATE" "$elapsed" "$cpu" "$rss"
}

start_status_loop() {
  (
    while true; do
      if [ -z "${ACTIVE_CHILD_PID:-}" ]; then
        break
      fi

      if ! kill -0 "$ACTIVE_CHILD_PID" 2>/dev/null; then
        break
      fi

      sleep 1
      print_runtime_status
    done
  ) &
  STATUS_PID=$!
}

start_hotkey_watcher() {
  (
    while true; do
      IFS= read -rsn1 key </dev/tty || exit 0
      case "$key" in
        q|Q)
          echo
          red_msg ">>> q erkannt → stoppe ALLES"
          if [ -n "${ACTIVE_PGID:-}" ]; then
            stop_process_group "$ACTIVE_PGID"
          fi
          exit 10
          ;;
        p|P)
          if [ -n "${ACTIVE_PGID:-}" ]; then
            toggle_pause_process_group "$ACTIVE_PGID"
          fi
          ;;
        r|R)
          echo
          blue_msg ">>> restart erkannt"
          if [ -n "${ACTIVE_PGID:-}" ]; then
            stop_process_group "$ACTIVE_PGID"
          fi
          exit 99
          ;;
        s|S)
          echo
          print_runtime_status
          ;;
      esac
    done
  ) &
  WATCHER_PID=$!
}

run_with_controls() {
  local cmd="$1"

  while true; do
    header "Starte Prozess"
    printf "${DIM}%s${RESET}\n" "$cmd"
    echo
    printf "${WHITE}Hotkeys live:${RESET} ${YELLOW}q${RESET}=Quit | ${YELLOW}p${RESET}=Pause/Resume | ${YELLOW}r${RESET}=Restart | ${YELLOW}s${RESET}=Status"
    echo
    echo

    bash -c "$cmd" &
    ACTIVE_CHILD_PID=$!
    ACTIVE_PGID="$(get_pgid "$ACTIVE_CHILD_PID")"
    PROCESS_STATE="running"

    start_status_loop
    start_hotkey_watcher

    local proc_exit=0
    local watcher_exit=0

    while true; do
      if ! is_running "$ACTIVE_CHILD_PID"; then
        wait "$ACTIVE_CHILD_PID" 2>/dev/null || proc_exit=$?
        break
      fi

      if [ -n "${WATCHER_PID:-}" ] && ! kill -0 "$WATCHER_PID" 2>/dev/null; then
        wait "$WATCHER_PID" 2>/dev/null || watcher_exit=$?
        if ! is_running "$ACTIVE_CHILD_PID"; then
          wait "$ACTIVE_CHILD_PID" 2>/dev/null || proc_exit=$?
        else
          wait "$ACTIVE_CHILD_PID" 2>/dev/null || proc_exit=$?
        fi
        break
      fi

      sleep 0.1
    done

    ACTIVE_CHILD_PID=""
    ACTIVE_PGID=""
    PROCESS_STATE="idle"

    cleanup_background_helpers

    echo
    echo

    if [ "$watcher_exit" -eq 99 ]; then
      blue_msg ">>> Prozess wird neu gestartet ..."
      sleep 1
      continue
    fi

    if [ "$proc_exit" -eq 0 ]; then
      green_msg "Fertig."
    else
      red_msg "Beendet (Exit $proc_exit)"
    fi

    break
  done

  pause_prompt
}

run_standard() {
  run_with_controls "$PYTHON_BIN main.py -p \"$CURRENT_PERIOD\" -t \"$CURRENT_TOP\" -mv \"$CURRENT_MIN_VOLUME\""
}

run_pro_fast() {
  run_with_controls "$PYTHON_BIN main.py --pro --fast -p \"$CURRENT_PERIOD\" -t \"$CURRENT_TOP\" -mv \"$CURRENT_MIN_VOLUME\""
}

run_live() {
  run_with_controls "$PYTHON_BIN main.py --live"
}

run_dashboard() {
  run_with_controls "$PYTHON_BIN main.py --dashboard"
}

run_tests() {
  run_with_controls "$PYTHON_BIN -m pytest -q"
}

run_pdf_report() {
  run_with_controls "$PYTHON_BIN -c 'from report_pdf import run; run()'"
}

main_menu() {
  while true; do
    header "TRADING TERMINAL"

    printf "${WHITE}1)${RESET} Standard\n"
    printf "${WHITE}2)${RESET} Pro Schnell\n"
    printf "${WHITE}3)${RESET} Live\n"
    printf "${WHITE}4)${RESET} Dashboard\n"
    printf "${WHITE}5)${RESET} Tests\n"
    printf "${WHITE}6)${RESET} PDF-Report\n"
    printf "${WHITE}7)${RESET} Exit\n"
    echo

    read -r -p "Auswahl: " choice

    case "$choice" in
      1) run_standard ;;
      2) run_pro_fast ;;
      3) run_live ;;
      4) run_dashboard ;;
      5) run_tests ;;
      6) run_pdf_report ;;
      7) exit 0 ;;
      q|Q) exit 0 ;;
      *)
        red_msg "Ungültige Auswahl"
        sleep 1
        ;;
    esac
  done
}

main_menu
