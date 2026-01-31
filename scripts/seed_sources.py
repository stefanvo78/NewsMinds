"""
Seed script to populate the database with default news sources.

Creates 40+ curated news sources covering:
- Wire services and global outlets
- Independent Canadian and European newspapers
- Technology and science publications
- Business and finance outlets
- Investigative journalism and policy sources

Usage:
    # Local (SQLite)
    DATABASE_URL=sqlite+aiosqlite:///./data/newsminds.db python scripts/seed_sources.py

    # Azure SQL
    DATABASE_URL="mssql+aioodbc://user:pass@server:1433/newsminds?driver=ODBC+Driver+18+for+SQL+Server" python scripts/seed_sources.py
"""

import asyncio
import os
import sys

# Add project root to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.api.models.source import Source

# ---------------------------------------------------------------------------
# Default news sources
# ---------------------------------------------------------------------------
# Each entry: (name, url, description, source_type, source_config)

DEFAULT_SOURCES = [
    # --- Wire Services & Global News ---
    (
        "Reuters",
        "https://www.reuters.com",
        "International news agency providing global news coverage",
        "rss",
        {
            "feed_url": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best"
        },
    ),
    (
        "Associated Press",
        "https://apnews.com",
        "American not-for-profit news agency",
        "rss",
        {"feed_url": "https://rsshub.app/apnews/topics/apf-topnews"},
    ),
    (
        "BBC News",
        "https://www.bbc.com/news",
        "British public broadcast news service with global reach",
        "rss",
        {"feed_url": "https://feeds.bbci.co.uk/news/rss.xml"},
    ),
    (
        "BBC News - Technology",
        "https://www.bbc.com/news/technology",
        "BBC technology news coverage",
        "rss",
        {"feed_url": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
    ),
    (
        "Al Jazeera",
        "https://www.aljazeera.com",
        "Qatar-based international news network",
        "rss",
        {"feed_url": "https://www.aljazeera.com/xml/rss/all.xml"},
    ),
    # --- Independent Newspapers ---
    (
        "The Guardian",
        "https://www.theguardian.com",
        "Scott Trust-owned British daily known for independent investigative journalism",
        "rss",
        {"feed_url": "https://www.theguardian.com/world/rss"},
    ),
    (
        "The Guardian - Technology",
        "https://www.theguardian.com/technology",
        "The Guardian's technology section",
        "rss",
        {"feed_url": "https://www.theguardian.com/technology/rss"},
    ),
    (
        "The Globe and Mail",
        "https://www.theglobeandmail.com",
        "Canada's national newspaper of record, editorially independent",
        "rss",
        {
            "feed_url": "https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/world/"
        },
    ),
    (
        "CBC News",
        "https://www.cbc.ca/news",
        "Canadian public broadcaster - independent and publicly funded",
        "rss",
        {"feed_url": "https://rss.cbc.ca/lineup/topstories.xml"},
    ),
    (
        "The Toronto Star",
        "https://www.thestar.com",
        "Canada's largest-circulation newspaper, guided by the Atkinson Principles",
        "rss",
        {
            "feed_url": "https://www.thestar.com/search/?f=rss&t=article&c=news*&l=50&s=start_time&sd=desc"
        },
    ),
    (
        "The Conversation",
        "https://theconversation.com",
        "Independent, not-for-profit news written by academic experts",
        "rss",
        {"feed_url": "https://theconversation.com/articles.atom"},
    ),
    # --- Technology & Science ---
    (
        "Ars Technica",
        "https://arstechnica.com",
        "In-depth technology news and analysis",
        "rss",
        {"feed_url": "https://feeds.arstechnica.com/arstechnica/index"},
    ),
    (
        "TechCrunch",
        "https://techcrunch.com",
        "Technology industry news and startup coverage",
        "rss",
        {"feed_url": "https://techcrunch.com/feed/"},
    ),
    (
        "The Verge",
        "https://www.theverge.com",
        "Technology, science, art, and culture news",
        "rss",
        {"feed_url": "https://www.theverge.com/rss/index.xml"},
    ),
    (
        "Wired",
        "https://www.wired.com",
        "Technology and culture magazine",
        "rss",
        {"feed_url": "https://www.wired.com/feed/rss"},
    ),
    (
        "MIT Technology Review",
        "https://www.technologyreview.com",
        "MIT's flagship publication on emerging technologies",
        "rss",
        {"feed_url": "https://www.technologyreview.com/feed/"},
    ),
    (
        "Hacker News",
        "https://news.ycombinator.com",
        "Y Combinator's social news site focused on tech and startups",
        "rss",
        {"feed_url": "https://hnrss.org/frontpage"},
    ),
    (
        "The Register",
        "https://www.theregister.com",
        "Independent IT news site",
        "rss",
        {"feed_url": "https://www.theregister.com/headlines.atom"},
    ),
    (
        "IEEE Spectrum",
        "https://spectrum.ieee.org",
        "Engineering and technology news from IEEE",
        "rss",
        {"feed_url": "https://spectrum.ieee.org/feeds/feed.rss"},
    ),
    # --- AI & Machine Learning ---
    (
        "AI News - NewsAPI",
        "https://newsapi.org",
        "Aggregated news about artificial intelligence via NewsAPI",
        "newsapi",
        {"query": "artificial intelligence OR machine learning", "language": "en"},
    ),
    (
        "OpenAI News - NewsAPI",
        "https://newsapi.org",
        "News about OpenAI, ChatGPT, and GPT models via NewsAPI",
        "newsapi",
        {"query": "OpenAI OR ChatGPT OR GPT-4", "language": "en"},
    ),
    (
        "AI Policy - NewsAPI",
        "https://newsapi.org",
        "AI regulation and policy news via NewsAPI",
        "newsapi",
        {"query": "AI regulation OR AI policy OR AI safety", "language": "en"},
    ),
    # --- Business & Finance ---
    (
        "Financial Times",
        "https://www.ft.com",
        "International business newspaper with global editorial independence",
        "rss",
        {"feed_url": "https://www.ft.com/rss/home"},
    ),
    (
        "The Economist",
        "https://www.economist.com",
        "Editorially independent international weekly on current affairs and economics",
        "rss",
        {"feed_url": "https://www.economist.com/international/rss.xml"},
    ),
    (
        "Handelsblatt (English)",
        "https://www.handelsblatt.com",
        "Germany's leading business and finance newspaper",
        "rss",
        {"feed_url": "https://www.handelsblatt.com/contentexport/feed/top"},
    ),
    # --- Security & Cybersecurity ---
    (
        "Krebs on Security",
        "https://krebsonsecurity.com",
        "In-depth security news and investigation by Brian Krebs",
        "rss",
        {"feed_url": "https://krebsonsecurity.com/feed/"},
    ),
    (
        "The Hacker News",
        "https://thehackernews.com",
        "Cybersecurity news and analysis",
        "rss",
        {"feed_url": "https://feeds.feedburner.com/TheHackersNews"},
    ),
    (
        "BleepingComputer",
        "https://www.bleepingcomputer.com",
        "Technology news with focus on security",
        "rss",
        {"feed_url": "https://www.bleepingcomputer.com/feed/"},
    ),
    (
        "Dark Reading",
        "https://www.darkreading.com",
        "Enterprise cybersecurity news and analysis",
        "rss",
        {"feed_url": "https://www.darkreading.com/rss.xml"},
    ),
    # --- Science ---
    (
        "Nature News",
        "https://www.nature.com",
        "Leading international scientific journal",
        "rss",
        {"feed_url": "https://www.nature.com/nature.rss"},
    ),
    (
        "Science Magazine",
        "https://www.science.org",
        "Peer-reviewed journal published by AAAS",
        "rss",
        {"feed_url": "https://www.science.org/rss/news_current.xml"},
    ),
    (
        "Phys.org",
        "https://phys.org",
        "Science, research, and technology news",
        "rss",
        {"feed_url": "https://phys.org/rss-feed/"},
    ),
    # --- Investigative & Independent Journalism ---
    (
        "The Intercept",
        "https://theintercept.com",
        "Non-profit investigative journalism outlet focused on accountability",
        "rss",
        {"feed_url": "https://theintercept.com/feed/?rss"},
    ),
    (
        "Bellingcat",
        "https://www.bellingcat.com",
        "Independent international collective of open-source investigators",
        "rss",
        {"feed_url": "https://www.bellingcat.com/feed/"},
    ),
    (
        "De Correspondent (English)",
        "https://thecorrespondent.com",
        "Dutch independent, ad-free journalism platform focused on structural issues",
        "rss",
        {"feed_url": "https://thecorrespondent.com/rss"},
    ),
    # --- European & International ---
    (
        "Der Spiegel (English)",
        "https://www.spiegel.de/international/",
        "Major German news magazine known for hard-hitting investigative reporting",
        "rss",
        {"feed_url": "https://www.spiegel.de/international/index.rss"},
    ),
    (
        "NRC (English)",
        "https://www.nrc.nl/english/",
        "Dutch quality newspaper known for independent, in-depth reporting",
        "rss",
        {"feed_url": "https://www.nrc.nl/rss/"},
    ),
    (
        "France 24 (English)",
        "https://www.france24.com/en/",
        "French public international news channel - English edition",
        "rss",
        {"feed_url": "https://www.france24.com/en/rss"},
    ),
    (
        "DW News (English)",
        "https://www.dw.com/en",
        "Deutsche Welle - Germany's publicly funded international broadcaster",
        "rss",
        {"feed_url": "https://rss.dw.com/rdf/rss-en-all"},
    ),
    (
        "Swiss Info (English)",
        "https://www.swissinfo.ch/eng",
        "Swiss public broadcaster - known for neutral, balanced international reporting",
        "rss",
        {"feed_url": "https://www.swissinfo.ch/eng/rss/top-news"},
    ),
    (
        "NHK World",
        "https://www3.nhk.or.jp/nhkworld/",
        "Japan's public broadcasting organization - English service",
        "rss",
        {"feed_url": "https://www3.nhk.or.jp/nhkworld/en/news/feeds/"},
    ),
    (
        "The Irish Times",
        "https://www.irishtimes.com",
        "Ireland's newspaper of record, editorially independent via trust ownership",
        "rss",
        {"feed_url": "https://www.irishtimes.com/cmlink/news-1.1319192"},
    ),
    (
        "EUobserver",
        "https://euobserver.com",
        "Independent, not-for-profit newspaper covering EU affairs from Brussels",
        "rss",
        {"feed_url": "https://euobserver.com/rss"},
    ),
    # --- Startup & VC Ecosystem ---
    (
        "Startup News - NewsAPI",
        "https://newsapi.org",
        "Startup and venture capital news via NewsAPI",
        "newsapi",
        {"query": "startup funding OR venture capital OR Series A", "language": "en"},
    ),
    (
        "Crypto & Web3 - NewsAPI",
        "https://newsapi.org",
        "Cryptocurrency and Web3 news via NewsAPI",
        "newsapi",
        {"query": "cryptocurrency OR bitcoin OR ethereum OR web3", "language": "en"},
    ),
]


async def seed_sources():
    """Insert default sources into the database, skipping any that already exist."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is required")
        print(
            "Example: DATABASE_URL=sqlite+aiosqlite:///./data/newsminds.db python scripts/seed_sources.py"
        )
        sys.exit(1)

    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get existing source names to avoid duplicates
        result = await session.execute(select(Source.name))
        existing_names = {row[0] for row in result.fetchall()}

        created = 0
        skipped = 0

        for name, url, description, source_type, source_config in DEFAULT_SOURCES:
            if name in existing_names:
                print(f"  SKIP  {name} (already exists)")
                skipped += 1
                continue

            source = Source(
                name=name,
                url=url,
                description=description,
                source_type=source_type,
                source_config=source_config,
                is_active=True,
            )
            session.add(source)
            print(f"  ADD   {name} ({source_type})")
            created += 1

        await session.commit()

    await engine.dispose()

    print(f"\nDone! Created {created} sources, skipped {skipped} existing.")


if __name__ == "__main__":
    asyncio.run(seed_sources())
