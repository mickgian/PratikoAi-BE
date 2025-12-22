"""Database models and dependencies for the application."""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import Session

from app.core.config import settings
from app.models.thread import Thread


# Convert postgres URL to async format (postgresql+asyncpg://)
def get_async_database_url(url: str) -> str:
    """Convert sync PostgreSQL URL to async format.

    Args:
        url: Synchronous PostgreSQL URL (postgresql://)

    Returns:
        Async PostgreSQL URL (postgresql+asyncpg://)
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


# Create async engine for database operations
async_database_url = get_async_database_url(settings.POSTGRES_URL)
async_engine = create_async_engine(async_database_url, echo=False, pool_pre_ping=True, pool_size=10, max_overflow=20)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


# DEV-162: Sync engine for analytics (fire-and-forget background writes)
# Uses the original sync URL (without asyncpg)
sync_engine = create_engine(settings.POSTGRES_URL, echo=False, pool_pre_ping=True, pool_size=5, max_overflow=5)


def get_sync_session() -> Session:
    """Get sync database session for analytics operations.

    Returns:
        Session: Sync database session for background analytics writes
    """
    return Session(sync_engine)


async def get_db():
    """Get async database session.

    Yields:
        AsyncSession: Database session for async operations
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


__all__ = ["Thread", "get_db", "AsyncSessionLocal", "get_sync_session", "sync_engine"]
