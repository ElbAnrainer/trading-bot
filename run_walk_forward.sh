#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

echo "======================================"
echo " Starte Walk-Forward-Report"
echo "======================================"
echo "Hinweis: Nur Simulation, keine echten Orders."
echo "Legacy-Report-Pfad: python walk_forward.py"
echo "======================================"

source .venv/bin/activate
export PYTHONPATH=.

python walk_forward.py

echo "======================================"
echo " Walk-Forward-Report fertig"
echo "======================================"
