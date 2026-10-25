#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

cleanup_generated() {
  find .github/scripts .github/src .github/tests -path '*/__pycache__' -type d -prune -exec rm -rf {} +
  rm -rf .github/.pytest_cache .github/.ruff_cache
}

ensure_dev_environment() {
  if [[ -x ".github/.venv/bin/python" ]] &&
    .github/.venv/bin/python -m pytest --version >/dev/null 2>&1 &&
    .github/.venv/bin/python -m ruff --version >/dev/null 2>&1; then
    return 0
  fi
  if command -v pytest >/dev/null 2>&1 && command -v ruff >/dev/null 2>&1; then
    return 0
  fi
  if [[ -f ".github/scripts/bootstrap-dev.sh" ]]; then
    echo "verify: dev tools missing; bootstrapping $(pwd)/.github/.venv" >&2
    bash .github/scripts/bootstrap-dev.sh
  fi
}

resolve_tooling() {
  PYTHON_BIN="${PYTHON_BIN:-python3}"
  PYTEST_CMD=(pytest)
  RUFF_CMD=(ruff)

  if [[ -x ".github/.venv/bin/python" ]]; then
    PYTHON_BIN=".github/.venv/bin/python"
    PYTEST_CMD=("$PYTHON_BIN" -m pytest)
    RUFF_CMD=("$PYTHON_BIN" -m ruff)
  fi
}

trap cleanup_generated EXIT
cleanup_generated
ensure_dev_environment
resolve_tooling

bash .github/scripts/guard_public_local_files.sh
PYTHONPATH=.github/src "$PYTHON_BIN" -m compileall .github/src .github/tests
PYTHONPATH=.github/src "$PYTHON_BIN" .github/scripts/validate_dependency_policy.py
PYTHONPATH=.github/src "$PYTHON_BIN" .github/scripts/validate_testing_ci_contract.py
PYTHONPATH=.github/src "${PYTEST_CMD[@]}" -q -p no:cacheprovider .github/tests
PYTHONPATH=.github/src "$PYTHON_BIN" .github/scripts/validate_data_contract.py
PYTHONPATH=.github/src "$PYTHON_BIN" .github/scripts/validate_dataset_consumption_contract.py
PYTHONPATH=.github/src "$PYTHON_BIN" .github/scripts/validate_agent_market_context_resources.py
if "${RUFF_CMD[@]}" --version >/dev/null 2>&1; then
  "${RUFF_CMD[@]}" check .github/src .github/tests
  "${RUFF_CMD[@]}" format --check .github/src .github/tests .github/scripts
else
  echo "ERROR: ruff is required for local verification." >&2
  echo "Fix: bash .github/scripts/bootstrap-dev.sh" >&2
  exit 1
fi
bash -n .github/scripts/start-auto-paper.sh .github/scripts/monitor-auto-paper.sh .github/scripts/guard_public_local_files.sh
"$PYTHON_BIN" -m py_compile .github/scripts/request.py .github/scripts/serve-auto-paper-monitor.py .github/scripts/validate_dependency_policy.py .github/scripts/validate_data_contract.py .github/scripts/validate_dataset_consumption_contract.py .github/scripts/validate_agent_market_context_resources.py
"$PYTHON_BIN" -m py_compile .github/scripts/validate_testing_ci_contract.py .github/scripts/ops-audit.py
