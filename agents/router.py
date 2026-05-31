from __future__ import annotations

from config import SETTINGS
from classifier import get_agent_bucket

from .base import SpecializedAgent, build_agent


def route_agent(error_type_id: str) -> SpecializedAgent:
    bucket = get_agent_bucket(error_type_id)
    agent_def = SETTINGS.agents.get(bucket)
    if agent_def is None:
        agent_def = next(iter(SETTINGS.agents.values()))
    return build_agent(agent_def)
