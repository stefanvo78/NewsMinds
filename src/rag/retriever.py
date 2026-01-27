"""
RAG Retriever - The complete retrieval pipeline.

This combines chunking, embedding, and retrieval into a simple interface.
"""

from src.rag.chunking import chunk_text
from src.rag.vector_store import VectorStore, vector_store


class RAGRetriever:
    """Complete RAG retrieval pipeline."""

    def __init__(self, collection_name: str = "articles"):
        self.store = vector_store
        if collection_name != "articles":
            self.store = VectorStore(collection_name)

    def ingest_document(
        self,
        text: str,
        metadata: dict | None = None,
        chunk_size: int = 500,
    ) -> int:
        """
        Ingest a document into the vector store.

        Args:
            text: The document text
            metadata: Metadata to attach (source_id, title, etc.)
            chunk_size: Size of chunks

        Returns:
            Number of chunks created
        """
        # Chunk the document
        chunks = chunk_text(
            text=text,
            chunk_size=chunk_size,
            metadata=metadata or {},
        )

        # Add to vector store
        self.store.add_chunks(chunks)

        return len(chunks)

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        source_id: str | None = None,
    ) -> list[dict]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: The user's question
            limit: Maximum number of results
            source_id: Optional filter by source

        Returns:
            List of relevant chunks with scores
        """
        return self.store.search(
            query=query,
            limit=limit,
            source_id=source_id,
        )

    def get_context(
        self,
        query: str,
        limit: int = 5,
        max_tokens: int = 3000,
    ) -> str:
        """
        Get formatted context for an LLM prompt.

        Args:
            query: The user's question
            limit: Maximum number of chunks to retrieve
            max_tokens: Approximate max tokens (chars / 4)

        Returns:
            Formatted context string
        """
        results = self.retrieve(query, limit=limit)

        context_parts = []
        current_length = 0
        max_chars = max_tokens * 4  # Rough estimate

        for result in results:
            text = result["text"]
            if current_length + len(text) > max_chars:
                break
            context_parts.append(f"[Source: {result['metadata'].get('title', 'Unknown')}]\n{text}")
            current_length += len(text)

        return "\n\n---\n\n".join(context_parts)


# Global instance
rag_retriever = RAGRetriever()