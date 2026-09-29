#!/usr/bin/env bash
# Roda o harness do ai-lab contra o trabalho de um app.
# Uso: ./check.sh [caminho-do-app] [adapter]
set -euo pipefail

APP="${1:-$HOME/Work/lab/cycling-coach}"
ADAPTER="${2:-cycling-coach}"
LAB="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$APP" ]; then
  echo "app nao encontrado: $APP" >&2
  exit 2
fi

cd "$LAB"
PYTHONPATH="$APP/src" python3 -m harness.run "$APP" "$ADAPTER"
