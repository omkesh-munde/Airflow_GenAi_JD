# AI Log Analyzer (LangChain + OpenAI + Airflow)

Python prototype that watches incoming logs, detects errors, classifies them, routes to specialized AI agents, and prints structured terminal output.

---

## 1) What this project does

- Watches `logs/` for new files in near real-time.
- Reads each new log file and extracts an error block.
- Classifies errors into: `db`, `infra`, `code`, `unknown`.
- Routes each error to a specialized agent powered by LangChain + OpenAI.
- Prints readable CLI output with colors and emoji/ascii fallback.
- Includes an Airflow DAG to run the pipeline from CLI-only environments (for example EC2 over SSM).

---

## 2) Project structure and role of each file

```text
project/
│── main.py
│── config.py
│── settings.toml
│── log_watcher.py
│── classifier.py
│── cli_ui.py
│── requirements.txt
│── agents/
│   │── __init__.py
│   │── base.py
│   │── db_agent.py
│   │── infra_agent.py
│   │── code_agent.py
│   │── router.py
│── dags/
│   │── log_ai_pipeline_dag.py
│── logs/
│── sample_logs/
```

### File-by-file purpose

- `main.py`
  - Entry point.
  - Starts watcher, handles pipeline flow per new log, supports `--simulate`.
  - Sends final result payloads to UI layer.

- `config.py`
  - Loads runtime config from `settings.toml`.
  - Resolves paths/model/retry settings.
  - Optionally sets `OPENAI_API_KEY` from config if env var is not already present.

- `settings.toml`
  - Central config file for:
    - watched folder paths
    - LLM model and temperature
    - retry behavior
    - optional OpenAI key

- `log_watcher.py`
  - Uses `watchdog` observer to monitor `logs/`.
  - Reads newly created files and prevents duplicate processing.
  - Extracts full error block using `ERROR`, `Traceback`, `Exception`.

- `classifier.py`
  - Keyword-based classification rules:
    - `db`, `infra`, `code`, `unknown`.

- `agents/base.py`
  - Shared LLM logic:
    - structured response schema (`root_cause`, `fix`, `severity`)
    - OpenAI call through LangChain
    - retry and graceful fallback.

- `agents/db_agent.py`, `agents/infra_agent.py`, `agents/code_agent.py`
  - Specialized prompts for each domain.

- `agents/router.py`
  - Routing logic:
    - `db -> DB agent`
    - `infra -> Infra agent`
    - `code -> Code agent`
    - `unknown -> Code agent`.

- `cli_ui.py`
  - Dedicated terminal rendering layer.
  - Displays startup/shutdown banners and colorized result panels.
  - Isolated presentation boundary to simplify future HTML UI replacement.

- `dags/log_ai_pipeline_dag.py`
  - Airflow DAG (`log_ai_pipeline`) that invokes this project.
  - Uses env-overridable repo/python paths.

- `sample_logs/`
  - Dummy test logs for prototype simulation.

- `logs/`
  - Runtime drop folder being monitored.

---

## 3) Step-by-step execution flow (what happens behind the scenes)

### A. Local run (`main.py`)

1. `main.py` loads environment variables (`python-dotenv`).
2. Config is read from `settings.toml` via `config.py`.
3. `LogWatcher` starts monitoring `logs/`.
4. If `--simulate` is passed, files from `sample_logs/` are copied into `logs/`.
5. Each file creation event triggers pipeline callback:
   - read file content
   - extract error block
   - classify error type
   - choose specialized agent
   - run LangChain/OpenAI analysis
   - render structured output using `cli_ui.py`.

### B. Agent analysis

1. Router selects one agent (`db`, `infra`, `code`).
2. Agent sends prompt + error text to `gpt-4o-mini` (`temperature=0`).
3. Response is parsed into structured fields:
   - `Root Cause`
   - `Fix`
   - `Severity`.

### C. Airflow run (`dags/log_ai_pipeline_dag.py`)

1. Airflow task runs subprocess:
   - `python main.py --simulate --simulate-delay 0.2`
2. App processes sample logs and prints results.
3. If manually interrupted (`Ctrl+C`), task is marked failed with `KeyboardInterrupt`.
4. If allowed to finish naturally, run completes successfully.

---

## 4) Setup and run

## Windows local

```powershell
cd "c:\Users\Admin\Desktop\AiflowAWSGenAI\project"
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# set key (recommended)
$env:OPENAI_API_KEY = "<your_key>"

# normal watch mode
.\.venv\Scripts\python main.py

# simulation mode
.\.venv\Scripts\python main.py --simulate --simulate-delay 0.2
```

## EC2 / Linux (SSM)

```bash
cd ~/ads/Airflow_GenAi_JD
source adsenv/bin/activate
pip install -r requirements.txt

export AIRFLOW_HOME=/home/ssm-user/airflow
mkdir -p "$AIRFLOW_HOME/dags"
cp -r dags/* "$AIRFLOW_HOME/dags/"

export OPENAI_API_KEY="<your_key>"
airflow dags test log_ai_pipeline 2026-04-17
```

### Monitor DAG runs from a second SSM tab (CLI-only)

Airflow 3.x CLI flag shapes can differ by build. On this project’s EC2 setup, the reliable pattern is:

```bash
airflow dags list-runs log_ai_pipeline
```

To auto-refresh every 2 seconds (no `watch` required):

```bash
while true; do airflow dags list-runs log_ai_pipeline; sleep 2; clear; done
```

Stop the loop with `Ctrl+C`.

---

## 5) Configuration

Update `settings.toml`:

- `[paths]`
  - `logs_dir`
  - `sample_logs_dir`
- `[llm]`
  - `model` (default `gpt-4o-mini`)
  - `temperature`
  - `max_retries`
  - `retry_backoff_s`
- `[openai]`
  - `api_key` (optional; env var is preferred)

---

## 6) Important behavior notes

- Duplicate files are not reprocessed in one process lifetime.
- Empty log and no-error logs are handled gracefully.
- If OpenAI key is missing, app returns safe fallback responses.
- Airflow warning for `graphviz` is non-blocking.
- For production Airflow, consider replacing watcher-style runtime with a bounded `run_once` executor script.

---

## 7) Future HTML UI migration plan

Current code already separates pipeline and presentation:

- pipeline output -> `ExecutionResult` object (`main.py`)
- rendering -> `CliUI` (`cli_ui.py`)

To move to HTML UI:

1. keep pipeline unchanged,
2. add web renderer/API using same `ExecutionResult` contract,
3. switch output sink from terminal renderer to web layer.

