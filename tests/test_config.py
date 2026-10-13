import os

from app.config import get_azure_settings


def test_settings_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embeddings")
    get_azure_settings.cache_clear()

    settings = get_azure_settings()

    assert settings.api_key == "test-key"
    assert settings.endpoint == "https://example.openai.azure.com/"
    assert settings.api_version == "2024-02-01"
    assert settings.embedding_deployment == "embeddings"
    get_azure_settings.cache_clear()


def test_importing_app_does_not_overwrite_environment(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "keep-me")

    import importlib

    import app.main
    importlib.reload(app.main)

    assert os.environ["AZURE_OPENAI_API_KEY"] == "keep-me"
