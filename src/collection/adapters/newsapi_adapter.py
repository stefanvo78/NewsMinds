"""NewsAPI.org adapter - fetches articles from the NewsAPI service."""

import logging
from datetime import datetime, timezone

import httpx

from src.api.core.config import settings

logger = logging.getLogger(__name__)

NEWSAPI_BASE_URL = "https://newsapi.org/v2"


async def fetch_newsapi_articles(
    query: str,
    language: str = "en",
    max_articles: int = 20,
    api_key: str | None = None,
) -> list[dict]:
    """
    Fetch articles from NewsAPI.org.

    Args:
        query: Search query (e.g. "artificial intelligence")
        language: Language code (default "en")
        max_articles: Maximum number of articles
        api_key: NewsAPI key (falls back to settings.NEWSAPI_KEY)

    Returns:
        List of article dicts with keys:
        title, url, content, author, published_at
    """
    key = api_key or getattr(settings, "NEWSAPI_KEY", None)
    if not key:
        logger.warning("NEWSAPI_KEY not configured, skipping NewsAPI fetch")
        return []

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{NEWSAPI_BASE_URL}/everything",
            params={
                "q": query,
                "language": language,
                "pageSize": min(max_articles, 100),
                "sortBy": "publishedAt",
            },
            headers={"X-Api-Key": key},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

    if data.get("status") != "ok":
        logger.error(f"NewsAPI error: {data.get('message')}")
        return []

    articles = []
    for item in data.get("articles", []):
        # NewsAPI returns truncated content (200 chars) on free tier
        # The full content is in item["content"] but often truncated
        content = item.get("content") or item.get("description") or ""

        published_at = None
        if item.get("publishedAt"):
            try:
                published_at = datetime.fromisoformat(
                    item["publishedAt"].replace("Z", "+00:00")
                )
            except ValueError:
                pass

        articles.append(
            {
                "title": item.get("title", "Untitled"),
                "url": item.get("url", ""),
                "content": content,
                "author": item.get("author"),
                "published_at": published_at,
            }
        )

    logger.info(f"Fetched {len(articles)} articles from NewsAPI for query '{query}'")
    return articles
