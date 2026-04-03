#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-.}"
BUNDLE="${BUNDLE:-./refactor_artifacts_bundle.zip}"
PDF_DOC="${PDF_DOC:-./Refactor_Dokumentation.pdf}"
DOCX_DOC="${DOCX_DOC:-./Refactor_Dokumentation.docx}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${PROJECT_DIR}/backup_refactor_${TIMESTAMP}"
TMP_DIR="${PROJECT_DIR}/.tmp_refactor_unpack_${TIMESTAMP}"

echo "Projektordner: ${PROJECT_DIR}"
echo "Bundle:       ${BUNDLE}"
echo "PDF:          ${PDF_DOC}"
echo "DOCX:         ${DOCX_DOC}"
echo "Backup nach:  ${BACKUP_DIR}"
echo

if [[ ! -d "${PROJECT_DIR}" ]]; then
  echo "Projektordner nicht gefunden: ${PROJECT_DIR}"
  exit 1
fi

if [[ ! -f "${BUNDLE}" ]]; then
  echo "Bundle nicht gefunden: ${BUNDLE}"
  echo "Lege refactor_artifacts_bundle.zip in den Projektordner oder setze BUNDLE=..."
  exit 1
fi

mkdir -p "${BACKUP_DIR}"
mkdir -p "${TMP_DIR}"

backup_file_if_exists() {
  local f="$1"
  if [[ -f "${PROJECT_DIR}/${f}" ]]; then
    mkdir -p "${BACKUP_DIR}/$(dirname "${f}")"
    cp "${PROJECT_DIR}/${f}" "${BACKUP_DIR}/${f}"
    echo "Backup erstellt: ${f}"
  fi
}

echo "Erstelle Backups ..."
backup_file_if_exists "main.py"
backup_file_if_exists "cli.py"
backup_file_if_exists "analysis_engine.py"
backup_file_if_exists ".gitignore"
backup_file_if_exists "docs/refactor/Refactor_Dokumentation.pdf"
backup_file_if_exists "docs/refactor/Refactor_Dokumentation.docx"

echo
echo "Entpacke Bundle ..."
unzip -oq "${BUNDLE}" -d "${TMP_DIR}"

# Finde Quellordner im ZIP
SOURCE_DIR=""
if [[ -d "${TMP_DIR}/refactor_artifacts" ]]; then
  SOURCE_DIR="${TMP_DIR}/refactor_artifacts"
else
  SOURCE_DIR="${TMP_DIR}"
fi

copy_if_exists() {
  local src="$1"
  local dst="$2"
  if [[ -f "${src}" ]]; then
    mkdir -p "$(dirname "${dst}")"
    cp "${src}" "${dst}"
    echo "Kopiert: ${dst}"
  else
    echo "Übersprungen, nicht im Bundle: ${src}"
  fi
}

echo
echo "Kopiere Refactor-Dateien ..."

copy_if_exists "${SOURCE_DIR}/main.py" "${PROJECT_DIR}/main.py"
copy_if_exists "${SOURCE_DIR}/cli.py" "${PROJECT_DIR}/cli.py"
copy_if_exists "${SOURCE_DIR}/analysis_engine.py" "${PROJECT_DIR}/analysis_engine.py"

# Doku lokal kopieren, wenn vorhanden
mkdir -p "${PROJECT_DIR}/docs/refactor"

if [[ -f "${PDF_DOC}" ]]; then
  cp "${PDF_DOC}" "${PROJECT_DIR}/docs/refactor/Refactor_Dokumentation.pdf"
  echo "Kopiert: ${PROJECT_DIR}/docs/refactor/Refactor_Dokumentation.pdf"
else
  echo "PDF lokal nicht gefunden, übersprungen: ${PDF_DOC}"
fi

if [[ -f "${DOCX_DOC}" ]]; then
  cp "${DOCX_DOC}" "${PROJECT_DIR}/docs/refactor/Refactor_Dokumentation.docx"
  echo "Kopiert: ${PROJECT_DIR}/docs/refactor/Refactor_Dokumentation.docx"
else
  echo "DOCX lokal nicht gefunden, übersprungen: ${DOCX_DOC}"
fi

# Optional: .gitignore ergänzen
if [[ -f "${PROJECT_DIR}/.gitignore" ]]; then
  if ! grep -q '^reports/$' "${PROJECT_DIR}/.gitignore"; then
    printf "\nreports/\n" >> "${PROJECT_DIR}/.gitignore"
    echo "Ergänzt: .gitignore um reports/"
  fi
else
  printf "reports/\n.venv/\n__pycache__/\n.pytest_cache/\n*.pyc\n.DS_Store\n" > "${PROJECT_DIR}/.gitignore"
  echo "Angelegt: .gitignore"
fi

rm -rf "${TMP_DIR}"

echo
echo "Fertig."
echo
echo "Als Nächstes:"
echo "  cd \"${PROJECT_DIR}\""
echo "  PYTHONPATH=. pytest -q"
echo "  python main.py"
