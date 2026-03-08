#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="airflow/docker-compose.yaml"
DC=(docker compose -f "${COMPOSE_FILE}")

usage() {
  cat <<'EOF'
Usage:
  scripts/airflow_control.sh up
  scripts/airflow_control.sh down
  scripts/airflow_control.sh status
  scripts/airflow_control.sh list-dags
  scripts/airflow_control.sh unpause-main
  scripts/airflow_control.sh pause-main
  scripts/airflow_control.sh trigger-hourly [start_date] [end_date] [age]

Examples:
  scripts/airflow_control.sh up
  scripts/airflow_control.sh trigger-hourly 2026-03-01 2026-03-08 22
EOF
}

json_escape() {
  local text="${1//\\/\\\\}"
  text="${text//\"/\\\"}"
  printf '%s' "${text}"
}

json_string_or_null() {
  local value="${1:-}"
  if [[ -n "${value}" ]]; then
    printf '"%s"' "$(json_escape "${value}")"
  else
    printf 'null'
  fi
}

require_compose_file() {
  if [[ ! -f "${COMPOSE_FILE}" ]]; then
    echo "[ERROR] compose file not found: ${COMPOSE_FILE}" >&2
    exit 1
  fi
}

cmd="${1:-}"
case "${cmd}" in
  up)
    require_compose_file
    "${DC[@]}" up airflow-init
    "${DC[@]}" up -d airflow-webserver airflow-scheduler airflow-worker airflow-triggerer
    ;;
  down)
    require_compose_file
    "${DC[@]}" down
    ;;
  status)
    require_compose_file
    "${DC[@]}" ps
    ;;
  list-dags)
    require_compose_file
    "${DC[@]}" exec airflow-webserver airflow dags list
    ;;
  unpause-main)
    require_compose_file
    "${DC[@]}" exec airflow-webserver airflow dags unpause lawdigest_hourly_update_dag
    "${DC[@]}" exec airflow-webserver airflow dags unpause lawdigest_daily_db_backup_dag
    ;;
  pause-main)
    require_compose_file
    "${DC[@]}" exec airflow-webserver airflow dags pause lawdigest_hourly_update_dag
    "${DC[@]}" exec airflow-webserver airflow dags pause lawdigest_daily_db_backup_dag
    ;;
  trigger-hourly)
    require_compose_file
    start_date="${2:-}"
    end_date="${3:-}"
    age="${4:-22}"
    conf=$(printf '{"start_date":%s,"end_date":%s,"age":"%s"}' \
      "$(json_string_or_null "${start_date}")" \
      "$(json_string_or_null "${end_date}")" \
      "$(json_escape "${age}")")
    "${DC[@]}" exec airflow-webserver airflow dags trigger lawdigest_hourly_update_dag --conf "${conf}"
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "[ERROR] unknown command: ${cmd}" >&2
    usage
    exit 1
    ;;
esac
