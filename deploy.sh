#!/usr/bin/env bash
set -euo pipefail

COMMIT_MSG="${1:-Refactor project structure and improve runtime}"

echo "==> Prüfe Projektstatus"
git status --short

echo
echo "==> .gitignore ergänzen"
touch .gitignore

for entry in "reports/" "backup_refactor_*/" "refactor_artifacts_bundle.zip" ".venv/" "__pycache__/" ".pytest_cache/" "*.pyc" ".DS_Store"
do
  grep -qxF "$entry" .gitignore || echo "$entry" >> .gitignore
done

echo
echo "==> Generierte Dateien aus Git entfernen"
git rm -r --cached reports 2>/dev/null || true
git rm -r --cached backup_refactor_* 2>/dev/null || true
git rm --cached refactor_artifacts_bundle.zip 2>/dev/null || true

echo
echo "==> Tests laufen"
PYTHONPATH=. pytest -q

echo
echo "==> Änderungen stagen"
git add .
git add -u

echo
echo "==> Commit erstellen"
if git diff --cached --quiet; then
  echo "Keine Änderungen zum Committen."
else
  git commit -m "$COMMIT_MSG"
fi

echo
echo "==> Pull (Rebase)"
git pull --rebase origin main

echo
echo "==> Letzte Commits:"
git log --oneline -3

echo
read -p "👉 Push nach GitHub durchführen? (y/n): " confirm

if [[ "$confirm" == "y" ]]; then
  git push origin main
  echo "✅ Push erfolgreich"
else
  echo "❌ Push abgebrochen"
fi
