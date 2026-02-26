"""
Pytest configuration and fixtures for the test suite.

This module provides common fixtures and configuration for all tests,
including database mocking and async support.
"""

import os

# DEV-300: Ensure POSTGRES_URL is set before any app imports so that
# modules like app.models.database don't fail during test collection.
if not os.environ.get("POSTGRES_URL"):
    os.environ["POSTGRES_URL"] = "postgresql://test:test@localhost:5432/pratikoai_test"

import asyncio
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from unittest.mock import (
    AsyncMock,
    Mock,
    patch,
)

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session.

    Overrides the default pytest-asyncio event_loop fixture to use
    session scope, ensuring all async fixtures share the same event loop.
    This prevents 'Event loop is closed' errors when disposing engines.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


def pytest_addoption(parser):
    """Add custom command-line options for Phase 9 tests."""
    parser.addoption(
        "--budget-cache",
        action="store",
        default=None,
        type=int,
        help="Cache operation budget in milliseconds (default: 25ms)",
    )
    parser.addoption(
        "--budget-llm",
        action="store",
        default=None,
        type=int,
        help="LLM wrapper budget in milliseconds (default: 400ms)",
    )
    parser.addoption(
        "--budget-tools",
        action="store",
        default=None,
        type=int,
        help="Tools wrapper budget in milliseconds (default: 200ms)",
    )
    parser.addoption(
        "--budget-stream",
        action="store",
        default=None,
        type=int,
        help="Streaming budget in milliseconds (default: 150ms)",
    )
    parser.addoption(
        "--budget-provider",
        action="store",
        default=None,
        type=int,
        help="Provider selection budget in milliseconds (default: 50ms)",
    )
    parser.addoption(
        "--budget-privacy",
        action="store",
        default=None,
        type=int,
        help="Privacy check budget in milliseconds (default: 30ms)",
    )
    parser.addoption(
        "--budget-golden",
        action="store",
        default=None,
        type=int,
        help="Golden lookup budget in milliseconds (default: 40ms)",
    )


@pytest.fixture(scope="session", autouse=True)
def set_budget_env_vars(request):
    """Set budget environment variables from CLI options."""
    budget_mappings = {
        "budget_cache": "RAG_BUDGET_P95_CACHE_MS",
        "budget_llm": "RAG_BUDGET_P95_LLM_MS",
        "budget_tools": "RAG_BUDGET_P95_TOOLS_MS",
        "budget_stream": "RAG_BUDGET_P95_STREAM_MS",
        "budget_provider": "RAG_BUDGET_P95_PROVIDER_MS",
        "budget_privacy": "RAG_BUDGET_P95_PRIVACY_MS",
        "budget_golden": "RAG_BUDGET_P95_GOLDEN_MS",
    }

    for opt_name, env_var in budget_mappings.items():
        value = request.config.getoption(f"--{opt_name.replace('_', '-')}")
        if value is not None:
            os.environ[env_var] = str(value)


@pytest.fixture
def mock_database_session():
    """Mock database session for testing."""
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.exec = Mock()
    return session


@pytest_asyncio.fixture
async def db_session():
    """Real async database session for integration tests.

    Creates a fresh engine and session for each test to avoid
    event loop conflicts between tests.
    """
    from app.models.database import get_async_database_url

    # Create a fresh engine for this test to avoid event loop issues
    async_database_url = get_async_database_url(settings.POSTGRES_URL)
    engine = create_async_engine(
        async_database_url,
        echo=False,
        pool_pre_ping=True,
    )

    # Create session factory
    test_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with test_session_maker() as session:
        yield session

    # Dispose of the engine after the test
    # Wrap in try/except to handle event loop closure during teardown
    try:
        await engine.dispose()
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise


@contextmanager
def assume_mock_database():
    """Context manager to assume mock database operations work correctly."""
    # In real tests, this would set up test database or mock objects
    # For now, it's a placeholder that allows tests to pass
    yield


# Add the fixture to pytest namespace
pytest.assume_mock_database = assume_mock_database


# ============================================================================
# Chat History Test Fixtures (Phase 4)
# ============================================================================

# Test database URL - use the same Docker PostgreSQL instance but different database
TEST_DATABASE_URL = "postgresql+asyncpg://aifinance:devpass@localhost:5433/aifinance_test"  # pragma: allowlist secret


@pytest_asyncio.fixture
async def test_db():
    """Create a test database session for tests.

    Each test gets a fresh database session. Data is cleaned up after
    the test completes to maintain isolation between tests.
    """
    # Create engine for this test
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

    # Ensure tables exist (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Create session factory
    TestingSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with TestingSessionLocal() as session:
        yield session
        # Commit any remaining changes
        await session.commit()
        await session.close()

    # Clean up: Delete test data after each test
    async with TestingSessionLocal() as cleanup_session:
        # Delete test user and related data (CASCADE will handle query_history)
        await cleanup_session.execute(text('DELETE FROM "user" WHERE id >= 99999'))
        await cleanup_session.commit()

    # Dispose engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(test_db):
    """Create a test user for chat history tests.

    Returns:
        User object with id, email, and other required fields
    """
    from app.models.user import User

    user = User(
        id=99999,  # Use high ID to avoid conflicts
        email="test_chat_user@example.com",
        full_name="Test Chat User",
        hashed_password="$2b$12$test_hashed_password_placeholder",
        role="regular_user",
        is_active=True,
        email_verified=True,
        provider="email",
        created_at=datetime.utcnow(),  # Use timezone-naive datetime for PostgreSQL
    )

    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    return user


@pytest_asyncio.fixture
async def test_session_id():
    """Create a test session ID for chat history tests."""
    return f"test-session-{uuid.uuid4()}"


@pytest_asyncio.fixture
async def sample_chat_messages(test_db, test_user, test_session_id):
    """Create sample chat messages for testing retrieval.

    Creates 3 sample messages in the test database for the test user.

    Returns:
        List of message IDs
    """
    from app.models.data_export import QueryHistory

    message_ids = []
    base_time = datetime.utcnow()

    messages = [
        {
            "query": "What is IVA in Italy?",
            "response": "IVA (Imposta sul Valore Aggiunto) is the Italian Value-Added Tax.",
            "tokens_used": 150,
            "cost_cents": 2,
        },
        {
            "query": "How much is the standard IVA rate?",
            "response": "The standard IVA rate in Italy is 22%.",
            "tokens_used": 120,
            "cost_cents": 1,
        },
        {
            "query": "Are there reduced IVA rates?",
            "response": "Yes, Italy has reduced IVA rates of 10%, 5%, and 4% for specific goods and services.",
            "tokens_used": 180,
            "cost_cents": 3,
        },
    ]

    for i, msg_data in enumerate(messages):
        message_id = str(uuid.uuid4())
        query_history = QueryHistory(
            id=message_id,
            user_id=test_user.id,
            session_id=test_session_id,
            query=msg_data["query"],
            response=msg_data["response"],
            model_used="gpt-4-turbo",
            tokens_used=msg_data["tokens_used"],
            cost_cents=msg_data["cost_cents"],
            response_cached=False,
            response_time_ms=1200 + i * 100,
            timestamp=base_time,
            created_at=base_time,
        )
        test_db.add(query_history)
        message_ids.append(message_id)

    await test_db.commit()

    return message_ids


@pytest.fixture
def auth_headers(test_user):
    """Create mock authentication headers for API tests.

    Returns:
        Dictionary with Authorization header containing a mock JWT token
    """
    # In real tests, you would generate a proper JWT token
    # For now, we'll use a mock token
    mock_token = f"test_token_user_{test_user.id}"
    return {"Authorization": f"Bearer {mock_token}"}
