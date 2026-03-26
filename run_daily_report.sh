#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

echo "======================================"
echo " Starte Daily Report"
echo "======================================"
echo "Hinweis: Nur Simulation, keine echten Orders."
echo "======================================"

source .venv/bin/activate
export PYTHONPATH=.

python main.py
python daily_report.py

echo "======================================"
echo " Daily Report fertig"
echo "======================================"
