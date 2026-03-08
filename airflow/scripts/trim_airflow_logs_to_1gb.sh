#!/usr/bin/env bash
set -euo pipefail

LOG_ROOT="${1:-/opt/airflow/logs}"
MAX_BYTES="${2:-1073741824}"  # 1 GiB
MIN_AGE_SECONDS="${MIN_AGE_SECONDS:-300}"

if [ ! -d "$LOG_ROOT" ]; then
  echo "[log-trim] skip: log root does not exist: $LOG_ROOT"
  exit 0
fi

bytes_to_human() {
  local bytes="$1"
  awk -v b="$bytes" 'BEGIN {
    split("B KiB MiB GiB TiB", u, " ");
    i = 1;
    while (b >= 1024 && i < 5) { b /= 1024; i++ }
    printf("%.2f %s", b, u[i]);
  }'
}

total_bytes="$(( $(find "$LOG_ROOT" -type f -printf '%s\n' 2>/dev/null | awk '{s+=$1} END{print s+0}') ))"

if [ "$total_bytes" -le "$MAX_BYTES" ]; then
  echo "[log-trim] within cap: $(bytes_to_human "$total_bytes") <= $(bytes_to_human "$MAX_BYTES")"
  exit 0
fi

echo "[log-trim] start prune: current=$(bytes_to_human "$total_bytes"), cap=$(bytes_to_human "$MAX_BYTES")"

now_epoch="$(date +%s)"
deleted_files=0
deleted_bytes=0

# oldest first
while IFS=$'\t' read -r mtime size path; do
  [ -n "$path" ] || continue

  mtime_epoch="${mtime%%.*}"
  age_seconds="$(( now_epoch - mtime_epoch ))"

  # Skip very new files to avoid racing actively written logs.
  if [ "$age_seconds" -lt "$MIN_AGE_SECONDS" ]; then
    continue
  fi

  if [ "$total_bytes" -le "$MAX_BYTES" ]; then
    break
  fi

  if rm -f -- "$path"; then
    total_bytes="$(( total_bytes - size ))"
    deleted_bytes="$(( deleted_bytes + size ))"
    deleted_files="$(( deleted_files + 1 ))"
  fi
done < <(find "$LOG_ROOT" -type f -printf '%T@\t%s\t%p\n' 2>/dev/null | sort -n)

find "$LOG_ROOT" -type d -empty -delete 2>/dev/null || true

echo "[log-trim] done: deleted_files=$deleted_files, reclaimed=$(bytes_to_human "$deleted_bytes"), now=$(bytes_to_human "$total_bytes")"

if [ "$total_bytes" -gt "$MAX_BYTES" ]; then
  echo "[log-trim] warning: still above cap, likely due active/new logs"
fi
