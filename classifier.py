from __future__ import annotations

import re


def classify_error(log_text: str) -> str:
    """
    Classify error text into one of: db, infra, code, unknown.
    Rules are intentionally simple keyword heuristics (prototype).
    """
    if not log_text or not log_text.strip():
        return "unknown"

    t = log_text.lower()

    # DB
    db_terms = [
        "sql",
        "psycopg2",
        "database",
        "connection refused",
        "could not connect",
        "relation does not exist",
        "deadlock",
        "timeout while connecting",
    ]
    if any(term in t for term in db_terms):
        return "db"

    # Infra
    infra_terms = [
        "timeout",
        "timed out",
        "network",
        "connection reset",
        "dns",
        "memory",
        "killed",
        "oom",
        "out of memory",
        "no space left",
    ]
    if any(term in t for term in infra_terms):
        return "infra"

    # Code
    code_terms = [
        "syntaxerror",
        "typeerror",
        "valueerror",
        "attributeerror",
        "importerror",
        "modulenotfounderror",
        "python error",
        "traceback",
        "exception",
    ]
    if any(term in t for term in code_terms):
        return "code"

    # Fallback: if it *looks* like a python exception line.
    if re.search(r"\b\w*error\b", t) or "exception" in t:
        return "code"

    return "unknown"

