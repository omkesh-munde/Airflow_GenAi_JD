from __future__ import annotations

import time
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from config import SETTINGS, AgentDef
from llm_factory import create_chat_model, llm_configured


class AgentResponse(BaseModel):
    root_cause: str = Field(..., description="Most likely root cause of the error.")
    fix: str = Field(..., description="Concrete fix steps or mitigations.")
    severity: str = Field(..., description="Estimated impact severity: Low, Medium, or High.")


@dataclass(frozen=True)
class SpecializedAgent:
    name: str
    system_prompt: str

    def analyze(
        self,
        error_text: str,
        *,
        error_type_id: str,
        error_label: str,
        pipeline_context: str,
        rag_context: str,
    ) -> AgentResponse:
        if not llm_configured():
            return AgentResponse(
                root_cause=(
                    f"LLM provider '{SETTINGS.llm_provider}' is not configured. "
                    "Set the appropriate API key environment variable or settings.toml entry."
                ),
                fix=(
                    f"Configure provider '{SETTINGS.llm_provider}' credentials. "
                    "Examples: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, "
                    "or use provider=ollama for local models."
                ),
                severity="Medium",
            )

        llm = create_chat_model()
        structured = llm.with_structured_output(AgentResponse)

        system_content = (
            f"{self.system_prompt}\n\n"
            "---\n"
            "Use the pipeline configuration below to tailor your analysis to this deployment.\n\n"
            f"{pipeline_context}\n\n"
            "---\n"
            "Similar past analyses from memory (RAG). Use them for pattern matching but verify against the current error:\n\n"
            f"{rag_context}"
        )

        human_content = (
            f"Classified error type: {error_type_id} ({error_label})\n\n"
            "Analyze this Airflow error text and return a structured response:\n\n"
            f"{error_text}"
        )

        last_err: Exception | None = None
        for attempt in range(1, SETTINGS.llm_max_retries + 1):
            try:
                return structured.invoke(
                    [
                        SystemMessage(content=system_content),
                        HumanMessage(content=human_content),
                    ]
                )
            except Exception as e:  # noqa: BLE001
                last_err = e
                if attempt >= SETTINGS.llm_max_retries:
                    break
                time.sleep(SETTINGS.llm_retry_backoff_s * attempt)

        return AgentResponse(
            root_cause=f"LLM call failed after {SETTINGS.llm_max_retries} attempts: {last_err}",
            fix="Verify provider credentials, model name, connectivity, and try again.",
            severity="Medium",
        )


def build_agent(agent_def: AgentDef) -> SpecializedAgent:
    return SpecializedAgent(name=agent_def.name, system_prompt=agent_def.system_prompt)
