#!/usr/bin/env bash
set -euo pipefail

# Stops processes started by scripts/start_live_stack.sh using PID files.
#
# Usage:
#   bash scripts/stop_live_stack.sh

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
RUNTIME_DIR="${PROJECT_ROOT}/runtime"

stop_from_pid_file() {
  local pid_file="$1"
  if [[ -f "${pid_file}" ]]; then
    local pid
    pid="$(cat "${pid_file}")"
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
      sleep 1
      kill -9 "${pid}" 2>/dev/null || true
      echo "Stopped PID ${pid} (${pid_file})"
    else
      echo "PID not running (${pid_file})"
    fi
    rm -f "${pid_file}"
  else
    echo "No pid file: ${pid_file}"
  fi
}

stop_from_pid_file "${RUNTIME_DIR}/ai-watcher.pid"
stop_from_pid_file "${RUNTIME_DIR}/airflow-scheduler.pid"
stop_from_pid_file "${RUNTIME_DIR}/airflow-api.pid"

echo "Live stack stop sequence completed."

