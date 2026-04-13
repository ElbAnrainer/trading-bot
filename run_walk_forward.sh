#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "======================================"
echo " Starte Walk-Forward-Report"
echo "======================================"
echo "Hinweis: Nur Simulation, keine echten Orders."
echo "Legacy-Report-Pfad: python walk_forward.py"
echo "======================================"

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

PYTHON_BIN="python"
[ -x ".venv/bin/python" ] && PYTHON_BIN=".venv/bin/python"

export PYTHONPATH="$PROJECT_ROOT"

"$PYTHON_BIN" walk_forward.py

echo "======================================"
echo " Walk-Forward-Report fertig"
echo "======================================"
