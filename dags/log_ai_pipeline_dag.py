from __future__ import annotations

import os
import subprocess
from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator


REPO_DIR = os.getenv("LOG_AI_REPO_DIR", "/home/ssm-user/ads/Airflow_GenAi_JD")
PYTHON_BIN = os.getenv("LOG_AI_PYTHON_BIN", "/home/ssm-user/ads/adsenv/bin/python")
MAIN_FILE = os.path.join(REPO_DIR, "main.py")


def run_log_ai_pipeline() -> None:
    """
    Execute one bounded run of the prototype.
    We call --simulate so the task exits (no endless folder-watch loop).
    """
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [PYTHON_BIN, MAIN_FILE, "--simulate", "--simulate-delay", "0.2"]
    subprocess.run(cmd, cwd=REPO_DIR, env=env, check=True)


with DAG(
    dag_id="log_ai_pipeline",
    start_date=datetime(2026, 4, 1),
    schedule="@hourly",
    catchup=False,
    tags=["logs", "ai", "prototype"],
) as dag:
    run_pipeline = PythonOperator(
        task_id="run_log_pipeline",
        python_callable=run_log_ai_pipeline,
    )

