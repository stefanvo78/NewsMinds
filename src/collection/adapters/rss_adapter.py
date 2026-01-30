"""RSS feed adapter - fetches articles from RSS/Atom feeds."""

import logging
from datetime import UTC, datetime

import feedparser
import httpx

logger = logging.getLogger(__name__)


async def fetch_rss_articles(
    feed_url: str,
    max_articles: int = 20,
) -> list[dict]:
    """
    Fetch articles from an RSS feed.

    Args:
        feed_url: URL of the RSS/Atom feed
        max_articles: Maximum number of articles to return

    Returns:
        List of article dicts with keys:
        title, url, content, author, published_at
    """
    # Fetch the feed (feedparser can parse from URL, but we use httpx
    # for async + custom headers)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            feed_url,
            headers={"User-Agent": "NewsMinds/1.0"},
            timeout=30.0,
        )
        response.raise_for_status()

    feed = feedparser.parse(response.text)

    articles = []
    for entry in feed.entries[:max_articles]:
        # Extract content - RSS feeds vary in structure
        content = ""
        if hasattr(entry, "content"):
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.summary
        elif hasattr(entry, "description"):
            content = entry.description

        # Parse published date
        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published_at = datetime(*entry.published_parsed[:6], tzinfo=UTC)

        articles.append(
            {
                "title": entry.get("title", "Untitled"),
                "url": entry.get("link", ""),
                "content": _strip_html(content),
                "author": entry.get("author", None),
                "published_at": published_at,
            }
        )

    logger.info(f"Fetched {len(articles)} articles from {feed_url}")
    return articles


def _strip_html(text: str) -> str:
    """Remove HTML tags from text. Simple approach."""
    import re

    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean
