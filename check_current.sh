#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "========================================"
echo " Prüfe aktuellen Projektstand"
echo "========================================"

if [[ ! -d ".venv" ]]; then
  echo "Fehler: .venv nicht gefunden"
  exit 1
fi

source .venv/bin/activate
export PYTHONPATH=.

echo
echo "1) Tests laufen ..."
pytest -q

echo
echo "2) Module prüfen ..."
python - <<'PY'
import importlib

modules = [
    "main",
    "analysis_engine",
    "output",
    "strategy",
    "data_loader",
    "journal",
    "performance",
    "dashboard",
    "cli",
    "broker",
]

for module_name in modules:
    importlib.import_module(module_name)

print("Alle Module erfolgreich importiert.")
PY

echo
echo "3) Dashboard bauen ..."
python - <<'PY'
from dashboard import build_dashboard
build_dashboard()
print("Dashboard erfolgreich gebaut.")
PY

echo
echo "4) Performance prüfen ..."
python - <<'PY'
from performance import print_performance
print_performance()
print("Performance-Modul erfolgreich ausgeführt.")
PY

echo
echo "========================================"
echo " Alles aktuell und lauffähig"
echo "========================================"
