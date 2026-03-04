#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${N8N_CONTAINER:-n8n}"
BROKER_PORT="${N8N_EXEC_BROKER_PORT:-5689}"

if [[ $# -lt 1 ]]; then
  echo "Usage: scripts/n8n_execute_with_safe_broker.sh [n8n execute args]" >&2
  echo "Example: scripts/n8n_execute_with_safe_broker.sh --id=VqZ4if5CN1vTtYhl" >&2
  exit 1
fi

echo "[n8n-exec] container=${CONTAINER} broker_port=${BROKER_PORT}" >&2

docker exec \
  -e N8N_RUNNERS_BROKER_PORT="${BROKER_PORT}" \
  "${CONTAINER}" \
  n8n execute "$@"
