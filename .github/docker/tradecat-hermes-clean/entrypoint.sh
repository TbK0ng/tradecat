#!/usr/bin/env bash
set -euo pipefail

export HERMES_HOME="${HERMES_HOME:-/home/ubuntu/.hermes}"
export CODEX_HOME="${CODEX_HOME:-/home/ubuntu/.codex}"
export TRADECAT_REPO="${TRADECAT_REPO:-/workspace/tradecat-public}"
export TRADECAT_PROJECT_SEED="${TRADECAT_PROJECT_SEED:-/opt/tradecat-public-seed}"
export TRADECAT_VENV="${TRADECAT_VENV:-/opt/tradecat-venv}"
export TRADECAT_RUNTIME_DIR="${TRADECAT_RUNTIME_DIR:-/home/ubuntu/.tradecat-runtime/auto-paper}"
export TRADECAT_AUTO_PAPER_RUNTIME_DIR="${TRADECAT_AUTO_PAPER_RUNTIME_DIR:-$TRADECAT_RUNTIME_DIR}"
export PATH="/opt/hermes-agent/.venv/bin:${TRADECAT_VENV}/bin:${PATH}"

if [[ "$(id -u)" == "0" ]]; then
  mkdir -p "${HERMES_HOME}" "${CODEX_HOME}" "${TRADECAT_REPO}" "${TRADECAT_VENV}" "$(dirname "${TRADECAT_RUNTIME_DIR}")"
  if [[ -d "${TRADECAT_PROJECT_SEED}" ]] \
    && [[ "${TRADECAT_CONTAINER_REFRESH_REPO:-0}" == "1" || ! -f "${TRADECAT_REPO}/pyproject.toml" ]]; then
    find "${TRADECAT_REPO}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
    cp -a "${TRADECAT_PROJECT_SEED}/." "${TRADECAT_REPO}/"
  fi
  chown -R ubuntu:ubuntu "${HERMES_HOME}" "${CODEX_HOME}" "${TRADECAT_REPO}" "${TRADECAT_VENV}" "$(dirname "${TRADECAT_RUNTIME_DIR}")"
  mkdir -p /run/sshd
  host_key_dir="/home/ubuntu/.tradecat-runtime/ssh-host-keys"
  mkdir -p "${host_key_dir}"
  if [[ ! -f "${host_key_dir}/ssh_host_ed25519_key" ]]; then
    ssh-keygen -t ed25519 -N "" -f "${host_key_dir}/ssh_host_ed25519_key" >/dev/null
  fi
  if [[ ! -f "${host_key_dir}/ssh_host_rsa_key" ]]; then
    ssh-keygen -t rsa -b 3072 -N "" -f "${host_key_dir}/ssh_host_rsa_key" >/dev/null
  fi
  cp "${host_key_dir}"/ssh_host_* /etc/ssh/
  chown root:root /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub
  chmod 600 /etc/ssh/ssh_host_*_key
  chmod 644 /etc/ssh/ssh_host_*_key.pub
  /usr/sbin/sshd
  exec gosu ubuntu "$0" "$@"
fi

mkdir -p \
  "${HERMES_HOME}/skills" \
  "${CODEX_HOME}/skills" \
  "${TRADECAT_RUNTIME_DIR}" \
  "${TRADECAT_REPO}/.github/.tools"

if [[ -d "${TRADECAT_REPO}/.github/skills/tradecat-public" ]]; then
  ln -sfn "${TRADECAT_REPO}/.github/skills/tradecat-public" "${HERMES_HOME}/skills/tradecat-public"
  ln -sfn "${TRADECAT_REPO}/.github/skills/tradecat-public" "${CODEX_HOME}/skills/tradecat-public"
fi

if [[ ! -x "${TRADECAT_VENV}/bin/python" ]]; then
  python3 -m venv "${TRADECAT_VENV}"
fi

if [[ -f "${TRADECAT_REPO}/pyproject.toml" ]]; then
  install_marker="${TRADECAT_VENV}/.tradecat-editable-installed"
  if [[ ! -f "${install_marker}" || "${TRADECAT_CONTAINER_REINSTALL:-0}" == "1" ]]; then
    "${TRADECAT_VENV}/bin/python" -m pip install --upgrade pip setuptools wheel
    "${TRADECAT_VENV}/bin/python" -m pip install \
      -c "${TRADECAT_REPO}/constraints.txt" \
      -e "${TRADECAT_REPO}[dev,report]"
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "${install_marker}"
  fi
fi

exec "$@"
