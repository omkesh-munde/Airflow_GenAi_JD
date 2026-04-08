from __future__ import annotations

from .base import SpecializedAgent


INFRA_AGENT = SpecializedAgent(
    name="Infra Agent",
    system_prompt=(
        "You are a DevOps engineer. Analyze infrastructure issues like memory, timeout, networking."
    ),
)

