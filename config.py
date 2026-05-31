from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ErrorTypeDef:
    id: str
    label: str
    agent: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class AgentDef:
    name: str
    system_prompt: str


@dataclass(frozen=True)
class PipelineMeta:
    name: str
    version: str
    description: str
    environment: str
    airflow_version: str
    dag_id: str
    executor: str


@dataclass(frozen=True)
class Settings:
    logs_dir: Path
    sample_logs_dir: Path
    value_doc_path: Path
    chroma_persist_dir: Path
    pipeline: PipelineMeta
    error_types: tuple[ErrorTypeDef, ...]
    agents: dict[str, AgentDef]
    llm_provider: str
    model: str
    temperature: float
    llm_max_retries: int
    llm_retry_backoff_s: float
    llm_base_url: str
    llm_api_key_env: str
    embedding_provider: str
    embedding_model: str
    embedding_api_key_env: str
    rag_enabled: bool
    rag_top_k: int
    rag_min_similarity: float
    web_enabled: bool
    web_host: str
    web_port: int
    provider_keys: dict[str, str] = field(default_factory=dict)
    ollama_base_url: str = "http://localhost:11434"
    azure_endpoint: str = ""
    azure_deployment: str = ""


def _resolve_path(base_dir: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (base_dir / p).resolve()


def _load_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _apply_provider_keys(data: dict) -> None:
    """Set provider API keys from config when env vars are not already set."""
    key_sections = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "groq": "GROQ_API_KEY",
        "azure": "AZURE_OPENAI_API_KEY",
    }
    for section, env_name in key_sections.items():
        block = data.get(section, {})
        api_key = str(block.get("api_key", "")).strip()
        if api_key and not os.getenv(env_name):
            os.environ[env_name] = api_key


def _load_error_types(base_dir: Path) -> tuple[ErrorTypeDef, ...]:
    raw = _load_toml(base_dir / "error_types.toml")
    items = raw.get("error_types", [])
    result: list[ErrorTypeDef] = []
    for item in items:
        result.append(
            ErrorTypeDef(
                id=str(item.get("id", "unknown")),
                label=str(item.get("label", "Unknown")),
                agent=str(item.get("agent", "code")),
                keywords=tuple(str(k).lower() for k in item.get("keywords", [])),
            )
        )
    return tuple(result)


def _load_agents(base_dir: Path) -> dict[str, AgentDef]:
    raw = _load_toml(base_dir / "agents.toml")
    agents_block = raw.get("agents", {})
    result: dict[str, AgentDef] = {}
    for key, value in agents_block.items():
        if not isinstance(value, dict):
            continue
        result[key] = AgentDef(
            name=str(value.get("name", key)),
            system_prompt=str(value.get("system_prompt", "")),
        )
    if not result:
        result["code"] = AgentDef(
            name="Generic Agent",
            system_prompt="You are an expert analyst. Diagnose the error and suggest fixes.",
        )
    return result


def load_settings() -> Settings:
    base_dir = Path(__file__).parent.resolve()
    data = _load_toml(base_dir / "settings.toml")
    _apply_provider_keys(data)

    paths = data.get("paths", {})
    pipeline = data.get("pipeline", {})
    llm = data.get("llm", {})
    embeddings = data.get("embeddings", {})
    rag = data.get("rag", {})
    web = data.get("web", {})
    ollama = data.get("ollama", {})
    azure = data.get("azure", {})

    provider_keys = {
        "openai": os.getenv("OPENAI_API_KEY", ""),
        "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
        "google": os.getenv("GOOGLE_API_KEY", ""),
        "groq": os.getenv("GROQ_API_KEY", ""),
        "azure": os.getenv("AZURE_OPENAI_API_KEY", ""),
    }

    return Settings(
        logs_dir=_resolve_path(base_dir, str(paths.get("logs_dir", "./logs"))),
        sample_logs_dir=_resolve_path(base_dir, str(paths.get("sample_logs_dir", "./sample_logs"))),
        value_doc_path=_resolve_path(base_dir, str(paths.get("value_doc_path", "./VALUE_PROPOSITION.md"))),
        chroma_persist_dir=_resolve_path(base_dir, str(paths.get("chroma_persist_dir", "./data/chroma"))),
        pipeline=PipelineMeta(
            name=str(pipeline.get("name", "Log AI Analyzer")),
            version=str(pipeline.get("version", "2.0")),
            description=str(pipeline.get("description", "")),
            environment=str(pipeline.get("environment", "local")),
            airflow_version=str(pipeline.get("airflow_version", "2.x")),
            dag_id=str(pipeline.get("dag_id", "")),
            executor=str(pipeline.get("executor", "")),
        ),
        error_types=_load_error_types(base_dir),
        agents=_load_agents(base_dir),
        llm_provider=str(llm.get("provider", "openai")).lower(),
        model=str(llm.get("model", "gpt-4o-mini")),
        temperature=float(llm.get("temperature", 0.0)),
        llm_max_retries=int(llm.get("max_retries", 3)),
        llm_retry_backoff_s=float(llm.get("retry_backoff_s", 1.5)),
        llm_base_url=str(llm.get("base_url", "")).strip(),
        llm_api_key_env=str(llm.get("api_key_env", "")).strip(),
        embedding_provider=str(embeddings.get("provider", "openai")).lower(),
        embedding_model=str(embeddings.get("model", "text-embedding-3-small")),
        embedding_api_key_env=str(embeddings.get("api_key_env", "")).strip(),
        rag_enabled=bool(rag.get("enabled", True)),
        rag_top_k=int(rag.get("top_k", 3)),
        rag_min_similarity=float(rag.get("min_similarity", 0.0)),
        web_enabled=bool(web.get("enabled", True)),
        web_host=str(web.get("host", "127.0.0.1")),
        web_port=int(web.get("port", 8080)),
        provider_keys=provider_keys,
        ollama_base_url=str(ollama.get("base_url", "http://localhost:11434")),
        azure_endpoint=str(azure.get("endpoint", "")),
        azure_deployment=str(azure.get("deployment", "")),
    )


SETTINGS = load_settings()
