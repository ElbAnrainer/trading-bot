#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

echo "Hinweis: run_walk_forwad.sh ist ein Legacy-Alias."
echo "Nutze bevorzugt ./run_walk_forward.sh"
exec bash ./run_walk_forward.sh
