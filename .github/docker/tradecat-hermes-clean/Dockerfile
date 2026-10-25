FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG CODEX_NPM_PACKAGE=@openai/codex
ARG CODEX_VERSION=0.133.0

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HERMES_HOME=/home/ubuntu/.hermes \
    CODEX_HOME=/home/ubuntu/.codex \
    TRADECAT_REPO=/workspace/tradecat-public \
    TRADECAT_PROJECT_SEED=/opt/tradecat-public-seed \
    TRADECAT_VENV=/opt/tradecat-venv \
    TRADECAT_RUNTIME_DIR=/home/ubuntu/.tradecat-runtime/auto-paper \
    TRADECAT_AUTO_PAPER_RUNTIME_DIR=/home/ubuntu/.tradecat-runtime/auto-paper

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        git \
        gosu \
        jq \
        netcat-openbsd \
        nodejs \
        npm \
        openssh-server \
        openssh-client \
        procps \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        ripgrep \
        tini \
    && npm install -g "${CODEX_NPM_PACKAGE}@${CODEX_VERSION}" \
    && npm cache clean --force \
    && rm -rf /var/lib/apt/lists/*

RUN if id ubuntu >/dev/null 2>&1; then \
        true; \
    elif getent passwd 1000 >/dev/null; then \
        existing_user="$(getent passwd 1000 | cut -d: -f1)" \
        && usermod --login ubuntu --home /home/ubuntu --move-home "${existing_user}" \
        && groupmod --new-name ubuntu "${existing_user}" || true; \
    else \
        useradd --create-home --shell /bin/bash --uid 1000 ubuntu; \
    fi \
    && mkdir -p /workspace /opt/hermes-agent /opt/tradecat-public-seed /opt/tradecat-venv /home/ubuntu/.codex /home/ubuntu/.tradecat-runtime \
    && echo 'ubuntu:ubuntu' | chpasswd \
    && chown -R ubuntu:ubuntu /workspace /opt/hermes-agent /opt/tradecat-public-seed /opt/tradecat-venv /home/ubuntu

RUN mkdir -p /etc/ssh/sshd_config.d /run/sshd \
    && printf '%s\n' \
        'Port 22' \
        'AddressFamily inet' \
        'PermitRootLogin no' \
        'PasswordAuthentication yes' \
        'KbdInteractiveAuthentication no' \
        'PubkeyAuthentication no' \
        'AllowUsers ubuntu' \
        'X11Forwarding no' \
        'AllowTcpForwarding no' \
        'PermitTunnel no' \
        'SetEnv HERMES_HOME=/home/ubuntu/.hermes CODEX_HOME=/home/ubuntu/.codex TRADECAT_REPO=/workspace/tradecat-public TRADECAT_PROJECT_SEED=/opt/tradecat-public-seed TRADECAT_VENV=/opt/tradecat-venv TRADECAT_RUNTIME_DIR=/home/ubuntu/.tradecat-runtime/auto-paper TRADECAT_AUTO_PAPER_RUNTIME_DIR=/home/ubuntu/.tradecat-runtime/auto-paper' \
        > /etc/ssh/sshd_config.d/99-tradecat-clean.conf

USER ubuntu
WORKDIR /opt

ARG HERMES_REPO=https://github.com/NousResearch/hermes-agent.git
ARG HERMES_REF=main
ARG HERMES_EXTRAS=messaging,mcp,cli

RUN git clone "${HERMES_REPO}" /opt/hermes-agent \
    && cd /opt/hermes-agent \
    && git checkout "${HERMES_REF}" \
    && python3 -m venv /opt/hermes-agent/.venv \
    && /opt/hermes-agent/.venv/bin/python -m pip install --upgrade pip setuptools wheel \
    && /opt/hermes-agent/.venv/bin/python -m pip install -e ".[${HERMES_EXTRAS}]"

ENV PATH=/opt/hermes-agent/.venv/bin:/opt/tradecat-venv/bin:$PATH

USER root
RUN ln -sf /opt/hermes-agent/.venv/bin/hermes /usr/local/bin/hermes \
    && printf '%s\n' '#!/usr/bin/env bash' 'exec /opt/tradecat-venv/bin/tradecat-auto "$@"' > /usr/local/bin/tradecat-auto \
    && printf '%s\n' '#!/usr/bin/env bash' 'exec /opt/tradecat-venv/bin/tradecat-agent "$@"' > /usr/local/bin/tradecat-agent \
    && chmod +x /usr/local/bin/tradecat-auto /usr/local/bin/tradecat-agent \
    && printf '%s\n' \
        'export HERMES_HOME="${HERMES_HOME:-/home/ubuntu/.hermes}"' \
        'export CODEX_HOME="${CODEX_HOME:-/home/ubuntu/.codex}"' \
        'export TRADECAT_REPO="${TRADECAT_REPO:-/workspace/tradecat-public}"' \
        'export TRADECAT_PROJECT_SEED="${TRADECAT_PROJECT_SEED:-/opt/tradecat-public-seed}"' \
        'export TRADECAT_VENV="${TRADECAT_VENV:-/opt/tradecat-venv}"' \
        'export TRADECAT_RUNTIME_DIR="${TRADECAT_RUNTIME_DIR:-/home/ubuntu/.tradecat-runtime/auto-paper}"' \
        'export TRADECAT_AUTO_PAPER_RUNTIME_DIR="${TRADECAT_AUTO_PAPER_RUNTIME_DIR:-${TRADECAT_RUNTIME_DIR}}"' \
        'export PATH=/opt/hermes-agent/.venv/bin:/opt/tradecat-venv/bin:$PATH' \
        > /etc/profile.d/tradecat-path.sh
COPY --chown=root:root .github/docker/tradecat-hermes-clean/entrypoint.sh /usr/local/bin/tradecat-hermes-entrypoint
RUN chmod +x /usr/local/bin/tradecat-hermes-entrypoint
COPY --chown=ubuntu:ubuntu . /opt/tradecat-public-seed

WORKDIR /workspace/tradecat-public
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/tradecat-hermes-entrypoint"]
CMD ["sleep", "infinity"]
