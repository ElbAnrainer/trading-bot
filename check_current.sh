#!/bin/bash
set -u

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT" || exit 1

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_DIR="reports/logs"
STATUS_DIR="reports/status"
LOG_FILE="$LOG_DIR/check_current_$TIMESTAMP.log"
LATEST_LOG="$LOG_DIR/check_current_latest.log"
STATUS_JSON="$STATUS_DIR/check_status_latest.json"

mkdir -p "$LOG_DIR"
mkdir -p "$STATUS_DIR"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "Log-Datei: $LOG_FILE"
echo

EXIT_CODE=0
WARN_COUNT=0
FAIL_COUNT=0
OK_COUNT=0

print_header() {
  echo "========================================"
  echo " $1"
  echo "========================================"
}

print_ok() {
  echo "[OK]    $1"
  OK_COUNT=$((OK_COUNT + 1))
}

print_warn() {
  echo "[WARN]  $1"
  WARN_COUNT=$((WARN_COUNT + 1))
}

print_fail() {
  echo "[FAIL]  $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
  EXIT_CODE=1
}

check_file() {
  local path="$1"
  if [ -f "$path" ]; then
    print_ok "Datei vorhanden: $path"
  else
    print_fail "Datei fehlt: $path"
  fi
}

check_dir() {
  local path="$1"
  if [ -d "$path" ]; then
    print_ok "Verzeichnis vorhanden: $path"
  else
    print_fail "Verzeichnis fehlt: $path"
  fi
}

print_header "Prüfe aktuellen Projektstand"

echo "Projektordner: $PROJECT_ROOT"
echo "Zeit: $(date)"
echo

print_header "1) Grundstruktur"

check_file "main.py"
check_file "analysis_engine.py"
check_file "output.py"
check_file "strategy.py"
check_file "report_pdf.py"
check_file "daily_report.py"
check_file "walk_forward.py"
check_file "gmail_api_report.py"
check_file "dependency_check.py"
check_file "env_loader.py"

check_file ".env.example"
check_file ".gitignore"
check_file "README_refactor.md"
check_file "SETUP_GMAIL_API.md"
check_file "SETUP_GITHUB_ACTIONS_MAIL.md"

check_file ".github/workflows/daily_report.yml"
check_file ".github/workflows/weekly_walk_forward.yml"

check_dir "reports"
check_dir "tests"

echo
print_header "2) Virtuelle Umgebung"

if [ -d ".venv" ]; then
  print_ok ".venv vorhanden"
else
  print_fail ".venv fehlt"
fi

if [ -x ".venv/bin/python" ]; then
  print_ok "Python in .venv gefunden"
else
  print_fail "Python in .venv nicht gefunden"
fi

if [ -x ".venv/bin/pytest" ]; then
  print_ok "pytest in .venv gefunden"
else
  print_fail "pytest in .venv nicht gefunden"
fi

echo
print_header "3) Python-Imports prüfen"

if [ -x ".venv/bin/python" ]; then
  PYTHONPATH=. .venv/bin/python - <<'PY'
import importlib
import sys

modules = [
    "main",
    "analysis_engine",
    "output",
    "strategy",
    "report_pdf",
    "daily_report",
    "walk_forward",
    "gmail_api_report",
    "dependency_check",
    "env_loader",
]

failed = False

for name in modules:
    try:
        importlib.import_module(name)
        print(f"[OK]    Modul importiert: {name}")
    except Exception as exc:
        failed = True
        print(f"[FAIL]  Modul nicht importierbar: {name} -> {exc}")

sys.exit(1 if failed else 0)
PY
  if [ $? -ne 0 ]; then
    EXIT_CODE=1
    FAIL_COUNT=$((FAIL_COUNT + 1))
  else
    OK_COUNT=$((OK_COUNT + 1))
  fi
else
  print_fail "Import-Prüfung übersprungen"
fi

echo
print_header "4) Dependency-Check"

if [ -x ".venv/bin/python" ]; then
  PYTHONPATH=. .venv/bin/python dependency_check.py
  if [ $? -eq 0 ]; then
    print_ok "Dependency-Check erfolgreich"
  else
    print_fail "Dependency-Check fehlgeschlagen"
  fi
else
  print_fail "Dependency-Check nicht möglich"
fi

echo
print_header "5) Tests"

if [ -x ".venv/bin/pytest" ]; then
  PYTHONPATH=. .venv/bin/pytest -q
  if [ $? -eq 0 ]; then
    print_ok "Alle Tests erfolgreich"
  else
    print_fail "Tests fehlgeschlagen"
  fi
else
  print_fail "pytest nicht gefunden"
fi

echo
print_header "6) Report-Erzeugung"

if [ -x ".venv/bin/python" ]; then
  PYTHONPATH=. .venv/bin/python report_pdf.py
  if [ $? -eq 0 ]; then
    print_ok "PDF-Report erfolgreich erzeugt"
  else
    print_fail "PDF-Report fehlgeschlagen"
  fi

  if [ -f "reports/trading_report_latest.pdf" ]; then
    print_ok "Latest PDF vorhanden"
  else
    print_fail "Latest PDF fehlt"
  fi

  PYTHONPATH=. .venv/bin/python daily_report.py
  if [ $? -eq 0 ]; then
    print_ok "Daily Report erfolgreich erzeugt"
  else
    print_fail "Daily Report fehlgeschlagen"
  fi

  PYTHONPATH=. .venv/bin/python walk_forward.py
  if [ $? -eq 0 ]; then
    print_ok "Walk-Forward erfolgreich erzeugt"
  else
    print_fail "Walk-Forward fehlgeschlagen"
  fi

  if [ -f "reports/walk_forward_latest.pdf" ]; then
    print_ok "Walk-Forward PDF vorhanden"
  else
    print_warn "Walk-Forward PDF fehlt"
  fi
else
  print_fail "Report-Erzeugung nicht möglich"
fi

echo
print_header "7) Mail-/OAuth-Konfiguration"

if [ -f ".env" ]; then
  print_ok ".env vorhanden"
else
  print_warn ".env fehlt (lokal für Mailversand relevant)"
fi

if [ -f "credentials_google.json" ]; then
  print_ok "credentials_google.json vorhanden"
else
  print_warn "credentials_google.json fehlt"
fi

if [ -f "token_google.json" ]; then
  print_ok "token_google.json vorhanden"
else
  print_warn "token_google.json fehlt"
fi

echo
print_header "8) Git-Status"

if command -v git >/dev/null 2>&1; then
  git status --short
  print_ok "git Status ausgegeben"
else
  print_warn "git nicht gefunden"
fi

echo
print_header "Monitoring-Zusammenfassung"

STATUS="GREEN"
if [ $FAIL_COUNT -gt 0 ]; then
  STATUS="RED"
elif [ $WARN_COUNT -gt 0 ]; then
  STATUS="YELLOW"
fi

echo "Status        : $STATUS"
echo "OK            : $OK_COUNT"
echo "Warnungen     : $WARN_COUNT"
echo "Fehler        : $FAIL_COUNT"
echo "Log-Datei     : $LOG_FILE"

cat > "$STATUS_JSON" <<EOF
{
  "timestamp": "$(date +"%Y-%m-%d %H:%M:%S")",
  "status": "$STATUS",
  "ok_count": $OK_COUNT,
  "warn_count": $WARN_COUNT,
  "fail_count": $FAIL_COUNT,
  "log_file": "$LOG_FILE"
}
EOF

cp "$LOG_FILE" "$LATEST_LOG"

if [ -x ".venv/bin/python" ]; then
  PYTHONPATH=. .venv/bin/python monitor_report.py
  if [ $? -eq 0 ]; then
    print_ok "HTML-Monitoring-Report erzeugt"
  else
    print_warn "HTML-Monitoring-Report konnte nicht erzeugt werden"
  fi
else
  print_warn "monitor_report.py nicht ausgeführt, da .venv/bin/python fehlt"
fi

echo
print_header "Fazit"

if [ $EXIT_CODE -eq 0 ]; then
  echo "Alles aktuell und lauffähig."
else
  echo "Es gibt mindestens ein Problem. Bitte die [FAIL]-Zeilen prüfen."
fi

echo "Latest Log: $LATEST_LOG"
echo "Status JSON: $STATUS_JSON"
echo "========================================"

exit $EXIT_CODE
