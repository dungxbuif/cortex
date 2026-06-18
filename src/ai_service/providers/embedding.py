from __future__ import annotations

from ai_service.core.ports import Embedder
from ai_service.providers.google_ai import GoogleAIClient


class GoogleEmbedder:
    def __init__(self, client: GoogleAIClient | None = None) -> None:
        self.client = client or GoogleAIClient()

    def embed_text(self, text: str) -> tuple[float, ...]:
        return self.client.embed_text(text)

    def embed_batch(self, texts: list[str]) -> list[tuple[float, ...]]:
        return [self.client.embed_text(text) for text in texts]


def default_embedder() -> Embedder:
    return GoogleEmbedder()
