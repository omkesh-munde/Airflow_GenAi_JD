#!/usr/bin/env bash
set -euo pipefail

# Prints status of runtime processes + recent logs.
#
# Usage:
#   bash scripts/status_live_stack.sh

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
RUNTIME_DIR="${PROJECT_ROOT}/runtime"

show_pid_status() {
  local label="$1"
  local pid_file="$2"
  if [[ -f "${pid_file}" ]]; then
    local pid
    pid="$(cat "${pid_file}")"
    if kill -0 "${pid}" 2>/dev/null; then
      echo "[RUNNING] ${label} (pid=${pid})"
    else
      echo "[STOPPED] ${label} (stale pid=${pid})"
    fi
  else
    echo "[UNKNOWN] ${label} (no pid file)"
  fi
}

show_pid_status "AI watcher" "${RUNTIME_DIR}/ai-watcher.pid"
show_pid_status "Airflow scheduler" "${RUNTIME_DIR}/airflow-scheduler.pid"
show_pid_status "Airflow API" "${RUNTIME_DIR}/airflow-api.pid"

echo
echo "Recent watcher log:"
tail -n 25 "${RUNTIME_DIR}/ai-watcher.log" 2>/dev/null || echo "(no watcher log yet)"

