from __future__ import annotations

from .base import SpecializedAgent


CODE_AGENT = SpecializedAgent(
    name="Code Agent",
    system_prompt="You are a Python and Airflow expert. Debug code-related issues.",
)

