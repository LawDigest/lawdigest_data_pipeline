#!/usr/bin/env bash
set -euo pipefail

WORKFLOW_FILE="${1:-n8n/workflows_export.json}"
CONTAINER="${N8N_CONTAINER:-n8n}"
REMOTE_PATH="/tmp/workflows_export.json"

if [[ ! -f "${WORKFLOW_FILE}" ]]; then
  echo "[n8n-import] workflow file not found: ${WORKFLOW_FILE}" >&2
  exit 1
fi

echo "[n8n-import] container=${CONTAINER}"
echo "[n8n-import] source=${WORKFLOW_FILE}"

docker cp "${WORKFLOW_FILE}" "${CONTAINER}:${REMOTE_PATH}"
docker exec "${CONTAINER}" sh -lc "n8n import:workflow --input=${REMOTE_PATH}"
docker exec "${CONTAINER}" sh -lc "n8n list:workflow | grep -F 'VqZ4if5CN1vTtYhl|lawdigest-bills-pipeline-v2' || true"
