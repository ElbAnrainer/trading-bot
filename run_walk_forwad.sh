#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

echo "======================================"
echo " Starte Walk-Forward-Test"
echo "======================================"
echo "Hinweis: Nur Simulation, keine echten Orders."
echo "======================================"

source .venv/bin/activate
export PYTHONPATH=.

python walk_forward.py

echo "======================================"
echo " Walk-Forward-Test fertig"
echo "======================================"
