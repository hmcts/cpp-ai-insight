import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class AzureOpenAISettings:
    api_key: str | None
    endpoint: str | None
    api_version: str | None
    embedding_deployment: str | None


@lru_cache
def get_azure_settings() -> AzureOpenAISettings:
    """Read Azure OpenAI settings from the environment (never written to it)."""
    return AzureOpenAISettings(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        embedding_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
    )
