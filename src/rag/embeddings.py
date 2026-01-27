"""
Embedding generation for RAG.

Embeddings convert text into vectors that capture semantic meaning.
Similar texts have similar vectors (close in vector space).
"""

from sentence_transformers import SentenceTransformer

from src.api.core.config import settings


class EmbeddingService:
    """Generate embeddings using sentence-transformers."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the model."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()

    def embed_text(self, text: str) -> list[float]:
        """Convert a single text to an embedding vector."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Convert multiple texts to embedding vectors (more efficient)."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()


# Global instance
embedding_service = EmbeddingService()