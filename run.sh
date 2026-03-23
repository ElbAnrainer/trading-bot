#!/bin/bash

cd "$(dirname "$0")"

echo "======================================"
echo " Starte Paper-Trading-Simulation"
echo "======================================"
echo "Hinweis: Es werden keine echten Orders ausgeführt."
echo "Dieses System dient nur für Backtesting, Simulation und persönliche Analyse."
echo "======================================"

source .venv/bin/activate

export PYTHONPATH=.

python main.py --top 5

echo "======================================"
echo " Simulation abgeschlossen"
echo "======================================"
