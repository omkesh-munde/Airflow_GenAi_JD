from __future__ import annotations

from config import SETTINGS, ErrorTypeDef


def _lookup_error_type(error_type_id: str) -> ErrorTypeDef | None:
    for et in SETTINGS.error_types:
        if et.id == error_type_id:
            return et
    return None


def classify_error(log_text: str) -> tuple[str, str]:
    """
    Classify error text into one of the configured Airflow error types.

    Returns:
        (error_type_id, human_label)
    """
    if not log_text or not log_text.strip():
        return "unknown", "Unknown"

    t = log_text.lower()

    for error_type in SETTINGS.error_types:
        if any(keyword in t for keyword in error_type.keywords):
            return error_type.id, error_type.label

    return "unknown", "Unknown"


def get_agent_bucket(error_type_id: str) -> str:
    """Map error type id to agent bucket (db | infra | code)."""
    if error_type_id == "unknown":
        return "code"
    et = _lookup_error_type(error_type_id)
    if et is None:
        return "code"
    return et.agent
