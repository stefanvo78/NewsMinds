"""
Document chunking for RAG.

Why chunk? LLMs have token limits, and smaller chunks = more precise retrieval.
"""

from dataclasses import dataclass


@dataclass
class Chunk:
    """A piece of a document."""

    text: str
    metadata: dict
    chunk_index: int


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    metadata: dict | None = None,
) -> list[Chunk]:
    """
    Split text into overlapping chunks.

    Args:
        text: The text to chunk
        chunk_size: Target size of each chunk (in characters)
        chunk_overlap: How much chunks should overlap
        metadata: Metadata to attach to each chunk

    Returns:
        List of Chunk objects
    """
    if metadata is None:
        metadata = {}

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        # Find the end of this chunk
        end = start + chunk_size

        # Try to break at a sentence boundary
        if end < len(text):
            # Look for sentence endings
            for sep in [". ", "! ", "? ", "\n\n", "\n"]:
                last_sep = text[start:end].rfind(sep)
                if last_sep != -1:
                    end = start + last_sep + len(sep)
                    break

        chunk_text = text[start:end].strip()

        if chunk_text:  # Don't add empty chunks
            chunks.append(
                Chunk(
                    text=chunk_text,
                    metadata={**metadata, "chunk_index": chunk_index},
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

        # Move start, accounting for overlap
        start = end - chunk_overlap

    return chunks
