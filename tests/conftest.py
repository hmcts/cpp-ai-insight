import pytest
from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings

from app.main import app
from app.metrics import azure_openai_embeddings


class FakeEmbeddings(Embeddings):
    """Deterministic bag-of-letters vectors, so identical texts score 1.0."""

    def _embed(self, text):
        vector = [0.0] * 26
        for ch in text.lower():
            if "a" <= ch <= "z":
                vector[ord(ch) - ord("a")] += 1.0
        return vector

    def embed_documents(self, texts):
        return [self._embed(t) for t in texts]

    def embed_query(self, text):
        return self._embed(text)


@pytest.fixture
def client():
    app.dependency_overrides[azure_openai_embeddings] = FakeEmbeddings
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()
