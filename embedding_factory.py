from __future__ import annotations

from langchain_core.embeddings import Embeddings

from config import SETTINGS


def create_embeddings() -> Embeddings:
    """
    Factory for provider-agnostic embedding models (used by RAG vector store).

    Supported providers (configure via settings.toml [embeddings] provider):
      openai | ollama | google | huggingface
    """
    provider = SETTINGS.embedding_provider
    model = SETTINGS.embedding_model

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=model)

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=model, base_url=SETTINGS.ollama_base_url)

    if provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(model=model)

    if provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=model)

    raise ValueError(
        f"Unsupported embedding provider '{provider}'. "
        "Use one of: openai, ollama, google, huggingface"
    )


def embeddings_configured() -> bool:
    provider = SETTINGS.embedding_provider
    if provider == "ollama":
        return True
    if provider == "huggingface":
        return True
    return bool(SETTINGS.provider_keys.get(provider))
