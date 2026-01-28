"""
Vector store interface using Qdrant.

Qdrant stores embeddings and allows fast similarity search.
"""

from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from src.api.core.config import settings
from src.rag.chunking import Chunk
from src.rag.embeddings import embedding_service


class VectorStore:
    """Interface to Qdrant vector database."""

    def __init__(self, collection_name: str = "articles"):
        self.collection_name = collection_name
        self._client: QdrantClient | None = None

    @property
    def client(self) -> QdrantClient:
        """Lazy initialize client."""
        if self._client is None:
            self._client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )
        return self._client

    def ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=embedding_service.dimension,
                    distance=Distance.COSINE,
                ),
            )

    def add_chunks(self, chunks: list[Chunk]) -> list[str]:
        """
        Add chunks to the vector store.

        Returns list of generated IDs.
        """
        self.ensure_collection()

        # Generate embeddings
        texts = [chunk.text for chunk in chunks]
        embeddings = embedding_service.embed_texts(texts)

        # Create points
        points = []
        ids = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            point_id = str(uuid4())
            ids.append(point_id)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": chunk.text,
                        **chunk.metadata,
                    },
                )
            )

        # Upsert to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        return ids

    def search(
        self,
        query: str,
        limit: int = 5,
        source_id: str | None = None,
    ) -> list[dict]:
        """
        Search for similar chunks.

        Args:
            query: The search query
            limit: Maximum number of results
            source_id: Optional filter by source

        Returns:
            List of matching chunks with scores
        """
        # Generate query embedding
        query_embedding = embedding_service.embed_text(query)

        # Build filter if needed
        search_filter = None
        if source_id:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="source_id",
                        match=MatchValue(value=source_id),
                    )
                ]
            )

        # Search using query_points (Qdrant client 1.7+)
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=limit,
            query_filter=search_filter,
        )

        # Format results
        return [
            {
                "id": point.id,
                "score": point.score,
                "text": point.payload.get("text", ""),
                "metadata": {k: v for k, v in point.payload.items() if k != "text"},
            }
            for point in results.points
        ]


# Global instance
vector_store = VectorStore()
