from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from config import SETTINGS


def _manual_vs_automated_table() -> str:
    return """| Capability | Manual monitoring | This utility |
|------------|-------------------|--------------|
| Error detection | Operator reads logs line-by-line | Automatic watch on `logs/` + keyword extraction |
| Classification | Tribal knowledge / guesswork | 15 configured Airflow error types with routing |
| Root-cause analysis | Requires senior engineer time | LLM specialist agents (db / infra / code) |
| Historical context | Hard to recall similar incidents | RAG vector store retrieves similar past analyses |
| Pipeline awareness | Analyst must know deployment details | Injects live pipeline config into every prompt |
| Response time | Minutes to hours | Seconds per log file |
| Consistency | Varies by on-call engineer | Structured output: root cause, fix, severity |
| Audit trail | Scattered tickets and chat | SQLite + Chroma persistent memory |
| LLM vendor lock-in | N/A | Provider-agnostic: OpenAI, Anthropic, Google, Ollama, Groq, Azure, HuggingFace |
| Scalability | Does not scale with log volume | Processes each new file independently, stores learnings |"""


def _value_bullets() -> str:
    return """1. **Faster MTTR** — Structured diagnosis and fix steps appear immediately instead of after manual triage.
2. **Institutional memory** — Every analysis is embedded and retrieved for similar future errors (RAG).
3. **Deployment-aware** — The LLM sees your pipeline name, executor, Airflow version, and error taxonomy.
4. **Reduced on-call load** — Routine Airflow failures are classified and explained without escalating to seniors.
5. **Portable AI stack** — Swap LLM or embedding providers via `settings.toml` without code changes.
6. **Airflow-native taxonomy** — 15 distinct error categories cover DAG, scheduler, worker, DB, K8s, and Celery failures."""


def update_value_document(
    *,
    file_path: Path,
    error_type: str,
    error_label: str,
    root_cause: str,
    fix: str,
    severity: str,
    rag_match_count: int,
    memory_stats: dict,
) -> None:
    """
    Regenerate VALUE_PROPOSITION.md after each analysis so stakeholders
    always see up-to-date value metrics vs manual monitoring.
    """
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    doc_path = SETTINGS.value_doc_path
    doc_path.parent.mkdir(parents=True, exist_ok=True)

    by_type_lines = "\n".join(
        f"- `{k}`: {v}" for k, v in memory_stats.get("by_error_type", {}).items()
    ) or "- (none yet)"

    by_sev_lines = "\n".join(
        f"- {k}: {v}" for k, v in memory_stats.get("by_severity", {}).items()
    ) or "- (none yet)"

    content = f"""# Value Proposition — {SETTINGS.pipeline.name}

> Auto-generated after each analysis. Last updated: **{now}** (UTC)

## Executive summary

**{SETTINGS.pipeline.name}** ({SETTINGS.pipeline.version}) automates Airflow log triage for environment **{SETTINGS.pipeline.environment}**.
It replaces slow, inconsistent manual log reading with AI-assisted classification, root-cause analysis, and fix recommendations — enriched by **RAG memory** of past incidents and **live pipeline configuration** context.

---

## How this adds value vs manual monitoring

{_manual_vs_automated_table()}

### Key benefits

{_value_bullets()}

---

## Live session metrics

| Metric | Value |
|--------|-------|
| Total analyses stored | {memory_stats.get('total_analyses', 0)} |
| RAG vector store active | {'Yes' if memory_stats.get('rag_available') else 'No (SQLite fallback)'} |
| LLM provider | `{SETTINGS.llm_provider}` / `{SETTINGS.model}` |
| Embedding provider | `{SETTINGS.embedding_provider}` / `{SETTINGS.embedding_model}` |
| Configured error types | {len(SETTINGS.error_types)} |
| Pipeline executor | {SETTINGS.pipeline.executor} |
| Airflow version target | {SETTINGS.pipeline.airflow_version} |

### Error type distribution (all time)

{by_type_lines}

### Severity distribution (all time)

{by_sev_lines}

---

## Latest analysis

| Field | Value |
|-------|-------|
| Timestamp (UTC) | {now} |
| File | `{file_path.name}` |
| Error type | `{error_type}` — {error_label} |
| Severity | **{severity}** |
| Similar past cases retrieved (RAG) | {rag_match_count} |

### Root cause

{root_cause.strip() or '(empty)'}

### Recommended fix

{fix.strip() or '(empty)'}

---

## Pipeline configuration snapshot

- **Name:** {SETTINGS.pipeline.name} v{SETTINGS.pipeline.version}
- **Description:** {SETTINGS.pipeline.description}
- **DAG ID:** {SETTINGS.pipeline.dag_id}
- **Environment:** {SETTINGS.pipeline.environment}
- **Logs directory:** `{SETTINGS.logs_dir}`
- **Memory store:** `{SETTINGS.chroma_persist_dir}`

---

## Manual monitoring pain points this solves

| Pain point | Without this tool | With this tool |
|------------|-------------------|----------------|
| Finding the error block in noisy logs | Scroll through thousands of lines | Automatic `ERROR` / `Traceback` extraction |
| Knowing if it's DB vs infra vs code | Requires Airflow expertise | Keyword + taxonomy routing to specialist agent |
| Remembering last week's similar outage | Search Slack / tickets | RAG retrieves top-{SETTINGS.rag_top_k} similar analyses |
| Explaining value to management | Anecdotal | This document updates after every run with metrics |
| Vendor AI lock-in | Single-provider scripts | Generic LLM + embedding factories |

---

*This file is regenerated automatically by `value_doc.py` on every successful analysis.*
"""

    doc_path.write_text(content, encoding="utf-8")
