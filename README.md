# Airflow Log AI Analyzer (Generic LLM + RAG)

Watches Airflow task logs, classifies **15 distinct error types**, retrieves similar past analyses from a vector store, injects **pipeline configuration context**, and routes to specialist AI agents.

---

## Features

- **15 Airflow error categories** — DAG import, timeout, scheduler, connections, XCom, sensors, pools, OOM, metadata DB, variables, permissions, Celery broker, DAG cycles, upstream failures, K8s pods
- **RAG memory** — SQLite + Chroma vector store; similar past errors appended to every LLM prompt
- **Pipeline context** — Live config from `settings.toml`, `error_types.toml`, and `agents.toml` injected into prompts
- **Generic LLM support** — OpenAI, Anthropic, Google, Ollama, Groq, Azure, HuggingFace (via `settings.toml`)
- **Value document** — `VALUE_PROPOSITION.md` auto-updates after each analysis with metrics vs manual monitoring
- **Web dashboard** — Audit history, charts, and pipeline stats at `http://127.0.0.1:8080` (auto-starts with `main.py`)

---

## Web dashboard

When `main.py` runs, a dashboard starts automatically (configurable in `settings.toml`):

```toml
[web]
enabled = true
host = "127.0.0.1"
port = 8080
```

Open **http://127.0.0.1:8080** to view:

- Live stats (total analyses, RAG status, LLM provider)
- Error type & severity charts
- Pipeline configuration snapshot
- Searchable **audit history** table with detail modal
- Auto-refresh every 5 seconds

Dashboard-only mode (no log watcher):

```powershell
python -m web.app
```

---

## Quick start (Windows)

```powershell
cd project
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:OPENAI_API_KEY = "<your_key>"

# Simulate all 15 sample Airflow errors
python main.py --simulate --simulate-delay 0.2
```

---

## Configuration

| File | Purpose |
|------|---------|
| `settings.toml` | Paths, LLM/embedding providers, RAG, pipeline metadata |
| `error_types.toml` | 15 error type definitions + keywords + agent routing |
| `agents.toml` | Specialist agent system prompts (db / infra / code) |

### Switch LLM provider

```toml
[llm]
provider = "anthropic"   # openai | anthropic | google | ollama | groq | azure | huggingface
model = "claude-3-5-haiku-latest"
```

Set the matching API key env var (`ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, etc.) or in `settings.toml`.

For **local Ollama**:

```toml
[llm]
provider = "ollama"
model = "llama3.2"

[embeddings]
provider = "ollama"
model = "nomic-embed-text"
```

---

## 15 Airflow error types

| ID | Label | Agent |
|----|-------|-------|
| `dag_import_error` | DAG Import / Broken DAG | code |
| `task_timeout` | Task Execution Timeout | infra |
| `scheduler_heartbeat` | Scheduler Heartbeat Failure | infra |
| `connection_not_found` | Connection Not Found | db |
| `xcom_error` | XCom Failure | code |
| `sensor_timeout` | Sensor Poke Timeout | infra |
| `pool_unavailable` | Pool Slot Unavailable | infra |
| `worker_oom` | Worker OOM | infra |
| `metadata_db_error` | Metadata DB Error | db |
| `variable_not_found` | Variable Not Found | code |
| `dag_file_permission` | DAG File Permission | infra |
| `celery_broker_disconnect` | Celery Broker Disconnect | infra |
| `dag_cycle` | DAG Cycle | code |
| `upstream_failed` | Upstream Task Failure | code |
| `kubernetes_pod_failure` | Kubernetes Pod Failure | infra |

Sample logs: `sample_logs/airflow_01_*.log` through `airflow_15_*.log`

---

## RAG memory

- **SQLite** (`data/chroma/analyses.sqlite`) — structured history
- **Chroma** (`data/chroma/`) — semantic retrieval of similar errors
- Falls back to keyword overlap if embeddings are unavailable

After each analysis, results are stored and retrieved for future prompts.

---

## Value document

`VALUE_PROPOSITION.md` is regenerated after every analysis with:

- Manual vs automated monitoring comparison
- Session metrics (total analyses, error distribution, RAG status)
- Latest analysis summary

---

## Airflow DAG

`dags/log_ai_pipeline_dag.py` runs a bounded simulate pass for EC2/SSM environments.

---

## Project structure

```text
project/
├── main.py
├── config.py
├── settings.toml
├── error_types.toml
├── agents.toml
├── llm_factory.py
├── embedding_factory.py
├── pipeline_context.py
├── value_doc.py
├── classifier.py
├── memory/store.py
├── agents/
├── sample_logs/        # 15 Airflow error samples
├── data/chroma/        # RAG store (gitignored)
└── VALUE_PROPOSITION.md
```
