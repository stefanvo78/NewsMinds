"""
Collection Service - fetches articles from configured sources.

Orchestrates the adapters and handles deduplication + storage + ingestion.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models import Source, Article
from src.collection.adapters.rss_adapter import fetch_rss_articles
from src.collection.adapters.newsapi_adapter import fetch_newsapi_articles
from src.rag.retriever import rag_retriever

logger = logging.getLogger(__name__)


async def collect_from_source(
    source: Source,
    db: AsyncSession,
) -> dict:
    """
    Collect articles from a single source.

    Returns:
        {"fetched": int, "new": int, "skipped": int, "ingested": int}
    """
    config = source.source_config or {}
    stats = {"fetched": 0, "new": 0, "skipped": 0, "ingested": 0}

    # Fetch articles based on source type
    try:
        if source.source_type == "rss":
            feed_url = config.get("feed_url")
            if not feed_url:
                logger.warning(f"Source '{source.name}' has no feed_url configured")
                return stats
            raw_articles = await fetch_rss_articles(
                feed_url=feed_url,
                max_articles=config.get("max_articles", 20),
            )

        elif source.source_type == "newsapi":
            query = config.get("query")
            if not query:
                logger.warning(f"Source '{source.name}' has no query configured")
                return stats
            raw_articles = await fetch_newsapi_articles(
                query=query,
                language=config.get("language", "en"),
                max_articles=config.get("max_articles", 20),
            )

        else:
            # "static" or unknown - skip
            logger.debug(f"Source '{source.name}' is type '{source.source_type}', skipping")
            return stats

    except Exception as e:
        logger.error(f"Failed to fetch from source '{source.name}': {e}")
        return stats

    stats["fetched"] = len(raw_articles)

    # Store articles (with deduplication by URL)
    for raw in raw_articles:
        url = raw.get("url", "")
        if not url:
            stats["skipped"] += 1
            continue

        # Check if article already exists
        result = await db.execute(select(Article).where(Article.url == url))
        if result.scalar_one_or_none():
            stats["skipped"] += 1
            continue

        # Create article
        article = Article(
            source_id=source.id,
            title=raw["title"],
            url=url,
            content=raw.get("content"),
            author=raw.get("author"),
            published_at=raw.get("published_at"),
            fetched_at=datetime.now(timezone.utc),
        )
        db.add(article)
        await db.flush()  # Get the ID without committing
        stats["new"] += 1

        # Ingest into Qdrant for RAG
        if article.content:
            try:
                metadata = {
                    "article_id": str(article.id),
                    "source_id": str(source.id),
                    "title": article.title,
                    "url": article.url,
                    "author": article.author or "Unknown",
                }
                if article.published_at:
                    metadata["published_at"] = article.published_at.isoformat()

                rag_retriever.ingest_document(
                    text=article.content,
                    metadata=metadata,
                    chunk_size=500,
                )
                stats["ingested"] += 1
            except Exception as e:
                logger.warning(f"Failed to ingest article to Qdrant: {e}")

    await db.commit()
    return stats


async def collect_all(db: AsyncSession) -> dict:
    """
    Collect from all active, non-static sources.

    Returns:
        {"sources_processed": int, "total_fetched": int,
         "total_new": int, "total_skipped": int, "total_ingested": int,
         "per_source": {source_name: stats}}
    """
    # Get all active sources that aren't static
    result = await db.execute(
        select(Source).where(
            Source.is_active.is_(True),
            Source.source_type != "static",
        )
    )
    sources = list(result.scalars().all())

    totals = {
        "sources_processed": len(sources),
        "total_fetched": 0,
        "total_new": 0,
        "total_skipped": 0,
        "total_ingested": 0,
        "per_source": {},
    }

    for source in sources:
        logger.info(f"Collecting from source: {source.name} ({source.source_type})")
        stats = await collect_from_source(source, db)
        totals["per_source"][source.name] = stats
        totals["total_fetched"] += stats["fetched"]
        totals["total_new"] += stats["new"]
        totals["total_skipped"] += stats["skipped"]
        totals["total_ingested"] += stats["ingested"]

    logger.info(
        f"Collection complete: {totals['total_new']} new articles "
        f"from {totals['sources_processed']} sources"
    )
    return totals