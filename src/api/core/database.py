"""
Async database connection using SQLAlchemy 2.0 with Azure SQL Server.

SQLAlchemy 2.0 uses:
- create_async_engine() for async connections
- AsyncSession for async database sessions
- The async_sessionmaker factory pattern

For Azure SQL, we use the aioodbc driver which provides async ODBC support.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.core.config import settings


# Determine engine kwargs based on database type
# SQLite doesn't support pool_size, max_overflow, pool_timeout
engine_kwargs = {
    "echo": settings.DEBUG,  # Log SQL statements when DEBUG=True
    "pool_pre_ping": True,  # Verify connections before using them
}

# Add pool settings only for non-SQLite databases
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_size": 5,  # Maximum number of connections to keep in the pool
            "max_overflow": 10,  # Allow 10 additional connections beyond pool_size
            "pool_timeout": 30,  # Seconds to wait for available connection
            "pool_recycle": 1800,  # Recycle connections after 30 minutes
        }
    )

# Create the async engine
# The engine manages the connection pool to the database
engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# SQLite: enable WAL mode and busy timeout for multi-worker concurrency.
# WAL allows concurrent readers alongside one writer.
# busy_timeout makes SQLite retry for 5 s instead of immediately failing
# with "database is locked".
if settings.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

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
