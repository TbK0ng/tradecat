#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/compose.tradecat-hermes.yml"
SERVICE="tradecat-hermes"

usage() {
  cat <<'EOF'
Usage: bash .github/scripts/tradecat-hermes-container.sh <command>

Commands:
  config   Validate Docker Compose configuration
  build    Build clean Ubuntu Hermes + TradeCat image
  up       Start idle clean service container
  down     Stop and remove service container, keep volumes
  shell    Open bash inside the clean container
  ssh      SSH into the clean container via 127.0.0.1:2222
  logs     Follow container logs
  status   Show container state and isolated volume names
  reset-agent-homes
           Recreate only Hermes/Codex home volumes, keep project/runtime/venv volumes
  refresh-project
           Replace the in-container project volume from the image seed
  verify   Run minimal in-container readiness checks

Local secret/config file:
  .github/docker/tradecat-hermes-clean/container.env
EOF
}

compose() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

case "${1:-}" in
  config)
    compose config
    ;;
  build)
    compose build
    ;;
  up)
    compose up -d
    ;;
  down)
    compose down
    ;;
  shell)
    compose exec --user ubuntu "${SERVICE}" bash
    ;;
  ssh)
    ssh -p 2222 \
      -o PreferredAuthentications=password \
      -o PubkeyAuthentication=no \
      -o StrictHostKeyChecking=accept-new \
      ubuntu@127.0.0.1
    ;;
  logs)
    compose logs -f "${SERVICE}"
    ;;
  status)
    compose ps
    docker volume ls --format '{{.Name}}' | grep -E 'tradecat_(project|hermes_home|codex_home|tradecat_venv|runtime)$' || true
    ;;
  reset-agent-homes)
    agent_home_volumes="$(
      docker inspect "${SERVICE}-clean" \
        --format '{{range .Mounts}}{{if or (eq .Destination "/home/ubuntu/.hermes") (eq .Destination "/home/ubuntu/.codex")}}{{println .Name}}{{end}}{{end}}' \
        2>/dev/null || true
    )"
    compose down
    if [[ -n "${agent_home_volumes}" ]]; then
      while IFS= read -r volume_name; do
        [[ -n "${volume_name}" ]] || continue
        docker volume rm "${volume_name}" >/dev/null
        echo "removed volume: ${volume_name}"
      done <<<"${agent_home_volumes}"
    fi
    compose up -d
    ;;
  refresh-project)
    compose exec -T --user root "${SERVICE}" bash -lc '
      set -euo pipefail
      : "${TRADECAT_REPO:=/workspace/tradecat-public}"
      : "${TRADECAT_PROJECT_SEED:=/opt/tradecat-public-seed}"
      test -d "${TRADECAT_PROJECT_SEED}"
      mkdir -p "${TRADECAT_REPO}"
      find "${TRADECAT_REPO}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
      cp -a "${TRADECAT_PROJECT_SEED}/." "${TRADECAT_REPO}/"
      chown -R ubuntu:ubuntu "${TRADECAT_REPO}"
    '
    ;;
  verify)
    compose exec -T --user ubuntu "${SERVICE}" bash -lc '
      set -euo pipefail
      hermes version
      codex --version
      node --version
      npm --version
      test -L "${CODEX_HOME}/skills/tradecat-public"
      python3 -m json.tool .github/skills/tradecat-public/agents/manifest.json >/dev/null
      bash .github/scripts/start-auto-paper.sh status --json >/dev/null || true
      bash .github/scripts/agent-smoke.sh
    '
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "unknown command: $1" >&2
    usage >&2
    exit 2
    ;;
esac
