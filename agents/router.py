from __future__ import annotations

from .base import SpecializedAgent
from .code_agent import CODE_AGENT
from .db_agent import DB_AGENT
from .infra_agent import INFRA_AGENT


def route_agent(error_type: str) -> SpecializedAgent:
    error_type = (error_type or "").strip().lower()
    if error_type == "db":
        return DB_AGENT
    if error_type == "infra":
        return INFRA_AGENT
    # unknown -> default to code agent
    return CODE_AGENT

