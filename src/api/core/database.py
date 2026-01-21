"""
Async database connection using SQLAlchemy 2.0 with Azure SQL Server.

SQLAlchemy 2.0 uses:
- create_async_engine() for async connections
- AsyncSession for async database sessions
- The async_sessionmaker factory pattern

For Azure SQL, we use the aioodbc driver which provides async ODBC support.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.core.config import settings


# Create the async engine
# The engine manages the connection pool to the database
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL statements when DEBUG=True
    pool_pre_ping=True,   # Verify connections before using them
)

# Create a session factory
# async_sessionmaker creates AsyncSession instances with consistent settings
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit (useful for returning data)
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    
    Usage in FastAPI:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    
    The session is automatically closed after the request completes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
