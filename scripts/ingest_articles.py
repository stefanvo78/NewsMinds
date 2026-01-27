"""
Article Ingestion Script - Sync articles from database to vector store.

This script reads articles from your SQL database and ingests them
into Qdrant for RAG retrieval.

Usage:
    # Ingest all articles
    python scripts/ingest_articles.py

    # Ingest only new articles (since last run)
    python scripts/ingest_articles.py --new-only

    # Ingest a specific article by ID
    python scripts/ingest_articles.py --article-id <uuid>
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.api.models import Article
from src.api.core.config import settings
from src.rag.retriever import rag_retriever


async def get_db_session() -> AsyncSession:
    """Create a database session."""
    # Use SQLite for local dev, or your configured DATABASE_URL
    db_url = settings.DATABASE_URL or "sqlite+aiosqlite:///./newsminds.db"
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    return async_session()


async def ingest_article(article: Article) -> int:
    """
    Ingest a single article into the vector store.
    
    Returns the number of chunks created.
    """
    # Skip articles without content
    if not article.content:
        print(f"  Skipping {article.id} - no content")
        return 0
    
    # Build metadata for retrieval filtering
    metadata = {
        "article_id": str(article.id),
        "source_id": str(article.source_id),
        "title": article.title,
        "url": article.url,
        "author": article.author or "Unknown",
    }
    
    # Add published date if available
    if article.published_at:
        metadata["published_at"] = article.published_at.isoformat()
    
    # Ingest into vector store
    num_chunks = rag_retriever.ingest_document(
        text=article.content,
        metadata=metadata,
        chunk_size=500,
    )
    
    return num_chunks


async def ingest_all_articles():
    """Ingest all articles from the database."""
    print("Starting full article ingestion...")
    
    async with await get_db_session() as session:
        result = await session.execute(select(Article))
        articles = result.scalars().all()
        
        print(f"Found {len(articles)} articles to ingest")
        
        total_chunks = 0
        for i, article in enumerate(articles, 1):
            print(f"[{i}/{len(articles)}] Ingesting: {article.title[:50]}...")
            chunks = await ingest_article(article)
            total_chunks += chunks
            print(f"  Created {chunks} chunks")
        
        print(f"\nDone! Ingested {len(articles)} articles into {total_chunks} chunks")


async def ingest_single_article(article_id: str):
    """Ingest a specific article by ID."""
    print(f"Ingesting article {article_id}...")
    
    async with await get_db_session() as session:
        result = await session.execute(
            select(Article).where(Article.id == article_id)
        )
        article = result.scalar_one_or_none()
        
        if not article:
            print(f"Article not found: {article_id}")
            return
        
        chunks = await ingest_article(article)
        print(f"Done! Created {chunks} chunks for '{article.title}'")


async def ingest_sample_data():
    """
    Ingest sample articles for testing (no database needed).
    
    Use this to test RAG without having articles in your DB.
    """
    print("Ingesting sample articles for testing...")
    
    sample_articles = [
        {
            "title": "OpenAI Announces GPT-5",
            "content": """OpenAI has announced GPT-5, the latest version of their 
            large language model. The new model shows significant improvements in 
            reasoning capabilities and can now solve complex mathematical problems 
            that previous versions struggled with. CEO Sam Altman stated that GPT-5 
            represents a major step toward artificial general intelligence. The model 
            will be available to ChatGPT Plus subscribers starting next month. 
            Enterprise customers will get early access through the API.""",
            "source": "Tech News Daily",
        },
        {
            "title": "Anthropic Releases Claude 4",
            "content": """Anthropic has released Claude 4, featuring enhanced 
            reasoning and a 500K token context window. The new model excels at 
            complex analysis tasks and code generation. Claude 4 introduces 
            'constitutional AI' improvements that make it more helpful while 
            maintaining strong safety guardrails. The model is available through 
            the Anthropic API and Claude.ai. Pricing remains competitive with 
            other frontier models.""",
            "source": "AI Weekly",
        },
        {
            "title": "Google DeepMind's New Breakthrough in Protein Folding",
            "content": """Google DeepMind has announced a breakthrough in protein 
            structure prediction. Their new AlphaFold 3 model can now predict 
            protein-ligand interactions with unprecedented accuracy. This has 
            major implications for drug discovery, potentially reducing the time 
            to develop new medications by years. Pharmaceutical companies are 
            already integrating the technology into their research pipelines. 
            The model will be made available to academic researchers for free.""",
            "source": "Science Today",
        },
        {
            "title": "EU Passes Comprehensive AI Regulation",
            "content": """The European Union has passed the AI Act, the world's 
            first comprehensive regulation of artificial intelligence. The law 
            categorizes AI systems by risk level and imposes strict requirements 
            on high-risk applications. Companies will have 24 months to comply 
            with most provisions. Tech industry groups have expressed concern 
            about compliance costs, while consumer advocates praise the law 
            as a necessary step to protect citizens from AI harms.""",
            "source": "European Tech Report",
        },
        {
            "title": "Microsoft Integrates AI Across Office Suite",
            "content": """Microsoft has rolled out Copilot AI integration across 
            its entire Office 365 suite. Users can now generate documents, 
            analyze spreadsheets, and create presentations using natural language 
            commands. Early adopters report productivity gains of 20-30% for 
            routine tasks. The feature is available to enterprise customers 
            with Microsoft 365 E3 and E5 licenses. Consumer rollout is 
            expected by Q3 2025.""",
            "source": "Business Tech Review",
        },
    ]
    
    total_chunks = 0
    for i, article in enumerate(sample_articles, 1):
        print(f"[{i}/{len(sample_articles)}] Ingesting: {article['title']}...")
        
        chunks = rag_retriever.ingest_document(
            text=article["content"],
            metadata={
                "title": article["title"],
                "source": article["source"],
                "article_id": f"sample-{i}",
            },
            chunk_size=500,
        )
        total_chunks += chunks
        print(f"  Created {chunks} chunks")
    
    print(f"\nDone! Ingested {len(sample_articles)} sample articles into {total_chunks} chunks")


def main():
    parser = argparse.ArgumentParser(description="Ingest articles into vector store")
    parser.add_argument("--article-id", help="Ingest a specific article by ID")
    parser.add_argument("--sample", action="store_true", help="Ingest sample test data")
    args = parser.parse_args()
    
    if args.sample:
        asyncio.run(ingest_sample_data())
    elif args.article_id:
        asyncio.run(ingest_single_article(args.article_id))
    else:
        asyncio.run(ingest_all_articles())


if __name__ == "__main__":
    main()
