from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from config import SETTINGS


def _provider_api_key(provider: str) -> str | None:
    if SETTINGS.llm_api_key_env:
        value = __import__("os").getenv(SETTINGS.llm_api_key_env)
        if value:
            return value
    return SETTINGS.provider_keys.get(provider) or None


def create_chat_model() -> BaseChatModel:
    """
    Factory for provider-agnostic chat models.

    Supported providers (configure via settings.toml [llm] provider):
      openai | anthropic | google | ollama | groq | azure | huggingface
    """
    provider = SETTINGS.llm_provider
    model = SETTINGS.model
    temperature = SETTINGS.temperature

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        kwargs: dict = {"model": model, "temperature": temperature}
        if SETTINGS.llm_base_url:
            kwargs["base_url"] = SETTINGS.llm_base_url
        return ChatOpenAI(**kwargs)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, temperature=temperature)

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, temperature=temperature)

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=model, base_url=SETTINGS.ollama_base_url, temperature=temperature)

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(model=model, temperature=temperature)

    if provider == "azure":
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_deployment=SETTINGS.azure_deployment or model,
            azure_endpoint=SETTINGS.azure_endpoint,
            temperature=temperature,
        )

    if provider == "huggingface":
        from langchain_huggingface import ChatHuggingFace

        return ChatHuggingFace(model_id=model, temperature=temperature)

    raise ValueError(
        f"Unsupported LLM provider '{provider}'. "
        "Use one of: openai, anthropic, google, ollama, groq, azure, huggingface"
    )


def llm_configured() -> bool:
    """Return True when the active provider has credentials or needs none (ollama)."""
    provider = SETTINGS.llm_provider
    if provider == "ollama":
        return True
    if provider == "azure":
        return bool(SETTINGS.azure_endpoint and (_provider_api_key("azure") or SETTINGS.azure_deployment))
    return bool(_provider_api_key(provider))
