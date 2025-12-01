"""pytest configuration for E2E integration tests.

Provides fixtures for:
- Test database with real PostgreSQL transactions
- Async session management with automatic rollback
- Test data cleanup

These fixtures enable true E2E testing with actual database operations,
catching integration bugs that mocked tests miss.
"""

import asyncio
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.core.config import settings

# Use test database (separate from dev/prod)
# NOTE: Ensure this database exists: CREATE DATABASE pratiko_ai_test;
TEST_DATABASE_URL = settings.POSTGRES_URL.replace("/pratiko_ai", "/pratiko_ai_test")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests.

    Scope: session - one loop for all tests
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine]:
    """Create test database engine and initialize schema.

    This fixture:
    1. Creates async engine for test database
    2. Creates all tables (runs migrations)
    3. Yields engine for tests
    4. Drops all tables after tests complete

    Scope: session - one engine for all tests
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,  # Verify connections before using
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Create database session with automatic rollback.

    Each test gets a fresh session that rolls back all changes,
    ensuring test isolation. This approach is faster than recreating
    tables and avoids test interference.

    Usage:
        async def test_something(db_session: AsyncSession):
            user = User(email="test@example.com")
            db_session.add(user)
            await db_session.commit()
            # Changes automatically rolled back after test

    Scope: function - new session for each test
    """
    async_session_maker = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session, session.begin():
        # Override app's get_db to use this test session
        from app.models.database import get_db

        async def override_get_db():
            yield session

        # Note: This override must be applied in each test
        # app.dependency_overrides[get_db] = override_get_db

        yield session

        # Rollback happens automatically when context exits
        await session.rollback()


@pytest.fixture(autouse=True)
async def reset_database_state(db_session: AsyncSession):
    """Reset database state before each test.

    This fixture runs automatically before each test (autouse=True)
    and ensures no leftover data from previous tests.

    Note: With transaction rollback, this is mostly redundant,
    but provides extra safety.
    """
    yield
    # Rollback handled by db_session fixture


@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """Override FastAPI's get_db dependency with test session.

    Usage:
        def test_something(override_get_db):
            # Now all API calls use test database session
            async with AsyncClient(app=app) as client:
                response = await client.get("/api/endpoint")
    """
    from app.main import app
    from app.models.database import get_db

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    yield

    # Clean up override
    app.dependency_overrides.pop(get_db, None)
