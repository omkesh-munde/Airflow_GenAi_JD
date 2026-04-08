from __future__ import annotations

from .base import SpecializedAgent


DB_AGENT = SpecializedAgent(
    name="DB Agent",
    system_prompt=(
        "You are a database expert. Analyze the error, identify root cause, and suggest fixes."
    ),
)

