from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    logs_dir: Path
    sample_logs_dir: Path
    model: str
    temperature: float

    # LLM retry (simple, best-effort)
    llm_max_retries: int
    llm_retry_backoff_s: float

    # Optional: loaded from config, but env var is still preferred
    openai_api_key: str | None = None


def _resolve_path(base_dir: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (base_dir / p).resolve()


def load_settings() -> Settings:
    """
    Load settings from `settings.toml` (recommended), with safe defaults.
    Also supports providing OPENAI key via config for local prototyping.
    """
    base_dir = Path(__file__).parent.resolve()
    settings_path = base_dir / "settings.toml"

    data: dict = {}
    if settings_path.exists():
        data = tomllib.loads(settings_path.read_text(encoding="utf-8"))

    paths = data.get("paths", {})
    llm = data.get("llm", {})
    openai = data.get("openai", {})

    logs_dir = _resolve_path(base_dir, str(paths.get("logs_dir", "./logs")))
    sample_logs_dir = _resolve_path(base_dir, str(paths.get("sample_logs_dir", "./sample_logs")))

    model = str(llm.get("model", "gpt-4o-mini"))
    temperature = float(llm.get("temperature", 0.0))
    max_retries = int(llm.get("max_retries", 3))
    retry_backoff_s = float(llm.get("retry_backoff_s", 1.5))

    api_key = str(openai.get("api_key", "")).strip() or None
    if api_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = api_key

    return Settings(
        logs_dir=logs_dir,
        sample_logs_dir=sample_logs_dir,
        model=model,
        temperature=temperature,
        llm_max_retries=max_retries,
        llm_retry_backoff_s=retry_backoff_s,
        openai_api_key=api_key,
    )


SETTINGS = load_settings()

