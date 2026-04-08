from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import SETTINGS


class AgentResponse(BaseModel):
    root_cause: str = Field(..., description="Most likely root cause of the error.")
    fix: str = Field(..., description="Concrete fix steps or mitigations.")
    severity: Literal["Low", "Medium", "High"] = Field(
        ..., description="Estimated impact severity."
    )


@dataclass(frozen=True)
class SpecializedAgent:
    name: str
    system_prompt: str

    def analyze(self, error_text: str) -> AgentResponse:
        if not os.getenv("OPENAI_API_KEY"):
            return AgentResponse(
                root_cause="Missing `OPENAI_API_KEY` (env) and no key set in `settings.toml`.",
                fix=(
                    "Set OPENAI_API_KEY as an environment variable, or put it in `settings.toml`.\n"
                    "PowerShell example:\n"
                    "  $env:OPENAI_API_KEY = \"<your_key>\""
                ),
                severity="Medium",
            )

        llm = ChatOpenAI(
            model=SETTINGS.model,
            temperature=SETTINGS.temperature,
        )
        structured = llm.with_structured_output(AgentResponse)

        last_err: Exception | None = None
        for attempt in range(1, SETTINGS.llm_max_retries + 1):
            try:
                return structured.invoke(
                    [
                        ("system", self.system_prompt),
                        (
                            "human",
                            "Analyze this error text and return a structured response:\n\n"
                            f"{error_text}",
                        ),
                    ]
                )
            except Exception as e:  # noqa: BLE001 (prototype retry)
                last_err = e
                if attempt >= SETTINGS.llm_max_retries:
                    break
                time.sleep(SETTINGS.llm_retry_backoff_s * attempt)

        return AgentResponse(
            root_cause=f"LLM call failed after {SETTINGS.llm_max_retries} attempts: {last_err}",
            fix="Verify API key, connectivity, and try again.",
            severity="Medium",
        )

