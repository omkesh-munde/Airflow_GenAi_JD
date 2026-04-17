#!/usr/bin/env bash
set -euo pipefail

# Starts long-running services in parallel:
# 1) Airflow scheduler
# 2) Optional Airflow API server (CLI/API access)
# 3) Realtime AI log watcher (main.py without --simulate)
#
# Usage:
#   bash scripts/start_live_stack.sh
#
# Optional env overrides:
#   PROJECT_ROOT=/home/ssm-user/ads/Airflow_GenAi_JD
#   AIRFLOW_HOME=/home/ssm-user/airflow
#   VENV_PATH=/home/ssm-user/ads/adsenv
#   START_AIRFLOW_API=1

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
AIRFLOW_HOME="${AIRFLOW_HOME:-/home/ssm-user/airflow}"
VENV_PATH="${VENV_PATH:-/home/ssm-user/ads/adsenv}"
START_AIRFLOW_API="${START_AIRFLOW_API:-0}"

source "${VENV_PATH}/bin/activate"
export AIRFLOW_HOME

mkdir -p "${AIRFLOW_HOME}/dags" "${PROJECT_ROOT}/runtime"

# Keep DAG files in sync for scheduler parsing.
cp -r "${PROJECT_ROOT}/dags/"* "${AIRFLOW_HOME}/dags/" 2>/dev/null || true

# Ensure metadata DB schema is initialized/upgraded.
airflow db migrate

echo "Starting Airflow scheduler..."
nohup airflow scheduler > "${PROJECT_ROOT}/runtime/airflow-scheduler.log" 2>&1 &
echo $! > "${PROJECT_ROOT}/runtime/airflow-scheduler.pid"

if [[ "${START_AIRFLOW_API}" == "1" ]]; then
  echo "Starting Airflow API server..."
  nohup airflow api-server > "${PROJECT_ROOT}/runtime/airflow-api.log" 2>&1 &
  echo $! > "${PROJECT_ROOT}/runtime/airflow-api.pid"
fi

echo "Starting realtime AI log watcher..."
nohup python "${PROJECT_ROOT}/main.py" > "${PROJECT_ROOT}/runtime/ai-watcher.log" 2>&1 &
echo $! > "${PROJECT_ROOT}/runtime/ai-watcher.pid"

echo
echo "Live stack started."
echo "PID files:"
echo "  ${PROJECT_ROOT}/runtime/airflow-scheduler.pid"
echo "  ${PROJECT_ROOT}/runtime/ai-watcher.pid"
if [[ "${START_AIRFLOW_API}" == "1" ]]; then
  echo "  ${PROJECT_ROOT}/runtime/airflow-api.pid"
fi
echo
echo "Tail logs:"
echo "  tail -f ${PROJECT_ROOT}/runtime/airflow-scheduler.log"
echo "  tail -f ${PROJECT_ROOT}/runtime/ai-watcher.log"

