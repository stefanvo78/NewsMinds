"""
Article management endpoints (CRUD).
"""

import uuid

from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select, func


from src.api.core.deps import DbSession, CurrentUser
from src.api.models import Article, Source
from src.api.schemas import (
    ArticleCreate,
    ArticleUpdate,
    ArticleResponse,
    ArticleListResponse,
)

from src.api.services.ai import ai_service
from src.rag.retriever import rag_retriever
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["Articles"])


@router.post("/", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    article_data: ArticleCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Article:
    """Create a new article."""
    # Verify source exists
    result = await db.execute(select(Source).where(Source.id == article_data.source_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source not found",
        )

    # Check if article URL already exists
    result = await db.execute(select(Article).where(Article.url == article_data.url))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Article with this URL already exists",
        )

    article = Article(**article_data.model_dump())
    db.add(article)
    await db.commit()
    await db.refresh(article)

    # Auto-ingest to Qdrant for RAG retrieval
    if article.content:
        try:
            metadata = {
                "article_id": str(article.id),
                "source_id": str(article.source_id),
                "title": article.title,
                "url": article.url,
                "author": article.author or "Unknown",
            }
            if article.published_at:
                metadata["published_at"] = article.published_at.isoformat()

            num_chunks = rag_retriever.ingest_document(
                text=article.content,
                metadata=metadata,
                chunk_size=500,
            )
            logger.info(f"Ingested article {article.id} into Qdrant ({num_chunks} chunks)")
        except Exception as e:
            # Don't fail article creation if Qdrant ingestion fails
            logger.warning(f"Failed to ingest article {article.id} to Qdrant: {e}")

    return article


@router.get("/", response_model=ArticleListResponse)
async def list_articles(
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    source_id: uuid.UUID | None = None,
) -> ArticleListResponse:
    """List articles with pagination."""
    # Base query
    query = select(Article)
    count_query = select(func.count(Article.id))

    # Filter by source if provided
    if source_id:
        query = query.where(Article.source_id == source_id)
        count_query = count_query.where(Article.source_id == source_id)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * per_page
    query = query.order_by(Article.fetched_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return ArticleListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: uuid.UUID, db: DbSession) -> Article:
    """Get a specific article by ID."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )
    return article


@router.patch("/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: uuid.UUID,
    article_data: ArticleUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Article:
    """Update an article (e.g., add AI-generated summary)."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    # Update only provided fields
    update_data = article_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(article, field, value)

    await db.commit()
    await db.refresh(article)
    return article


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete an article."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    await db.delete(article)
    await db.commit()


@router.post("/{article_id}/summarize")
async def summarize_article(
    article_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """
    Generate an AI summary for an article.

    Uses Claude to create a concise 2-3 sentence summary
    of the article's content.
    """
    # First, check if AI service is available
    if not ai_service.is_available:
        raise HTTPException(status_code=503, detail="AI service not configured")

    # Get the article from database
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Generate the summary
    summary = await ai_service.summarize_article(title=article.title, content=article.content)

    return {"article_id": str(article_id), "summary": summary}


@router.post("/{article_id}/ingest")
async def ingest_article_to_qdrant(
    article_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """
    Manually ingest an article into the Qdrant vector store.

    This is useful for re-indexing or ingesting articles that
    were created before auto-ingestion was enabled.
    """
    # Get the article from database
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if not article.content:
        raise HTTPException(status_code=400, detail="Article has no content to ingest")

    # Ingest to Qdrant
    try:
        metadata = {
            "article_id": str(article.id),
            "source_id": str(article.source_id),
            "title": article.title,
            "url": article.url,
            "author": article.author or "Unknown",
        }
        if article.published_at:
            metadata["published_at"] = article.published_at.isoformat()

        num_chunks = rag_retriever.ingest_document(
            text=article.content,
            metadata=metadata,
            chunk_size=500,
        )

        return {
            "article_id": str(article_id),
            "status": "ingested",
            "chunks_created": num_chunks,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/ingest-all")
async def ingest_all_articles_to_qdrant(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """
    Ingest all articles from the database into Qdrant.

    This is a bulk operation for initial setup or re-indexing.
    """
    # Get all articles with content
    result = await db.execute(select(Article).where(Article.content.isnot(None)))
    articles = result.scalars().all()

    total_chunks = 0
    ingested = 0
    failed = 0

    for article in articles:
        try:
            metadata = {
                "article_id": str(article.id),
                "source_id": str(article.source_id),
                "title": article.title,
                "url": article.url,
                "author": article.author or "Unknown",
            }
            if article.published_at:
                metadata["published_at"] = article.published_at.isoformat()

            num_chunks = rag_retriever.ingest_document(
                text=article.content,
                metadata=metadata,
                chunk_size=500,
            )
            total_chunks += num_chunks
            ingested += 1
        except Exception as e:
            logger.warning(f"Failed to ingest article {article.id}: {e}")
            failed += 1

    return {
        "status": "complete",
        "articles_ingested": ingested,
        "articles_failed": failed,
        "total_chunks_created": total_chunks,
    }
