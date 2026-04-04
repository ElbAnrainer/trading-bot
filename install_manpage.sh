#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
SOURCE_FILE="$PROJECT_ROOT/docs/manual/trading-bot.1"

choose_target_dir() {
  local explicit_target="${1:-}"
  local manpath_output dir candidate

  if [ -n "$explicit_target" ]; then
    printf '%s\n' "$explicit_target"
    return 0
  fi

  manpath_output="$(manpath 2>/dev/null || true)"
  [ -z "$manpath_output" ] && return 1

  OLD_IFS="$IFS"
  IFS=":"
  for dir in $manpath_output; do
    candidate="${dir%/}/man1"
    if [ -d "$candidate" ] && [ -w "$candidate" ]; then
      printf '%s\n' "$candidate"
      IFS="$OLD_IFS"
      return 0
    fi
  done
  IFS="$OLD_IFS"

  return 1
}

main() {
  local target_dir target_file
  target_dir="$(choose_target_dir "${1:-}")" || {
    echo "Kein beschreibbarer man1-Zielordner im aktuellen MANPATH gefunden." >&2
    exit 1
  }

  target_file="${target_dir%/}/trading-bot.1"
  install -m 0644 "$SOURCE_FILE" "$target_file"

  echo "Manpage installiert:"
  echo "  $target_file"
  echo
  echo "Test:"
  echo "  man trading-bot"
}

main "${1:-}"
