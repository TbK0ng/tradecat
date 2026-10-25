#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$ROOT_DIR"

if command -v uv >/dev/null 2>&1; then
  uv venv .github/.venv
  if [[ -f constraints.txt ]]; then
    uv pip install --python .github/.venv/bin/python -c constraints.txt -e ".[dev]"
  else
    uv pip install --python .github/.venv/bin/python -e ".[dev]"
  fi
else
  "$PYTHON_BIN" -m venv .github/.venv
  .github/.venv/bin/python -m pip install -U pip
  if [[ -f constraints.txt ]]; then
    .github/.venv/bin/python -m pip install -c constraints.txt -e ".[dev]"
  else
    .github/.venv/bin/python -m pip install -e ".[dev]"
  fi
fi

echo "dev environment ready: $ROOT_DIR/.github/.venv"
