#!/usr/bin/env bash
# Roda o harness do ai-lab contra o trabalho de um app.
#
# Uso: ./check.sh [caminho-do-app]
#
# O runner nao sabe nada do dominio do app: ele carrega <app>/evals/graders.py
# por caminho. Por isso o segundo argumento (nome de adapter) saiu — adapter
# agora e o proprio arquivo do app, nao um diretorio deste repo.
set -euo pipefail

APP="${1:-$HOME/Work/lab/cycling-coach}"
LAB="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$APP" ]; then
  echo "app nao encontrado: $APP" >&2
  exit 2
fi

cd "$LAB"
exec python3 -m harness.run "$APP"
