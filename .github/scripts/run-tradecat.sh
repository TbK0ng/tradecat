#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ -x "$ROOT_DIR/.github/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.github/.venv/bin/python"
fi

cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR/.github/src:${PYTHONPATH:-}"
if [[ "${1:-}" == "auto" ]]; then
  shift
fi
exec "$PYTHON_BIN" -m tradecat_auto.cli "$@"
