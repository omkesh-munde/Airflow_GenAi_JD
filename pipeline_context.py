from __future__ import annotations

import json
from datetime import datetime, timezone

from config import SETTINGS


def build_pipeline_context() -> str:
    """
    Serialize the pipeline's unique configuration for LLM context injection.
    """
    error_type_lines = [
        f"  - {et.id} ({et.label}) -> agent:{et.agent}"
        for et in SETTINGS.error_types
    ]
    agent_lines = [
        f"  - {key}: {agent.name}"
        for key, agent in SETTINGS.agents.items()
    ]

    payload = {
        "pipeline": {
            "name": SETTINGS.pipeline.name,
            "version": SETTINGS.pipeline.version,
            "description": SETTINGS.pipeline.description,
            "environment": SETTINGS.pipeline.environment,
            "airflow_version": SETTINGS.pipeline.airflow_version,
            "dag_id": SETTINGS.pipeline.dag_id,
            "executor": SETTINGS.pipeline.executor,
        },
        "llm": {
            "provider": SETTINGS.llm_provider,
            "model": SETTINGS.model,
            "temperature": SETTINGS.temperature,
        },
        "embeddings": {
            "provider": SETTINGS.embedding_provider,
            "model": SETTINGS.embedding_model,
        },
        "rag": {
            "enabled": SETTINGS.rag_enabled,
            "top_k": SETTINGS.rag_top_k,
        },
        "paths": {
            "logs_dir": str(SETTINGS.logs_dir),
            "sample_logs_dir": str(SETTINGS.sample_logs_dir),
        },
        "error_types_count": len(SETTINGS.error_types),
        "error_types": [et.id for et in SETTINGS.error_types],
        "agents": list(SETTINGS.agents.keys()),
    }

    return (
        "## Active Pipeline Configuration\n"
        f"- Name: {SETTINGS.pipeline.name} v{SETTINGS.pipeline.version}\n"
        f"- Environment: {SETTINGS.pipeline.environment}\n"
        f"- Airflow: {SETTINGS.pipeline.airflow_version} | Executor: {SETTINGS.pipeline.executor}\n"
        f"- DAG ID: {SETTINGS.pipeline.dag_id}\n"
        f"- LLM: {SETTINGS.llm_provider}/{SETTINGS.model}\n"
        f"- Embeddings: {SETTINGS.embedding_provider}/{SETTINGS.embedding_model}\n"
        f"- RAG: {'enabled' if SETTINGS.rag_enabled else 'disabled'} (top_k={SETTINGS.rag_top_k})\n"
        f"- Configured error types ({len(SETTINGS.error_types)}):\n"
        + "\n".join(error_type_lines)
        + "\n- Specialist agents:\n"
        + "\n".join(agent_lines)
        + "\n\n### Machine-readable config\n```json\n"
        + json.dumps(payload, indent=2)
        + "\n```"
    )


def format_rag_context(matches: list[dict]) -> str:
    """Format retrieved similar analyses for prompt injection."""
    if not matches:
        return "No similar past analyses found in memory."

    blocks: list[str] = []
    for i, match in enumerate(matches, start=1):
        blocks.append(
            f"### Past case {i} (relevance_score={match.get('score', 'n/a')})\n"
            f"- Error type: {match.get('error_type', 'unknown')} ({match.get('error_label', '')})\n"
            f"- File: {match.get('file_name', 'n/a')}\n"
            f"- When: {match.get('timestamp', 'n/a')}\n"
            f"- Root cause: {match.get('root_cause', '')}\n"
            f"- Fix applied: {match.get('fix', '')}\n"
            f"- Severity: {match.get('severity', '')}\n"
            f"- Error excerpt:\n```\n{match.get('error_excerpt', '')[:800]}\n```"
        )
    return "\n\n".join(blocks)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
