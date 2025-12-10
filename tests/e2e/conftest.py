"""pytest configuration for E2E integration tests.

Provides fixtures for:
- Async database sessions using existing app infrastructure
- Test data cleanup with automatic rollback
- LLM call tracking for golden set verification
- Expert profile for auto-approval testing
- Rate limiting for RSS feed tests

These fixtures enable true E2E testing with actual database operations,
catching integration bugs that mocked tests miss.

DEV-BE-69 Phase 6: E2E Testing for RSS Feeds and Scrapers
"""

import asyncio
import os
from datetime import datetime
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.database import get_async_database_url


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create database session for E2E tests.

    Creates a fresh engine and session for each test to avoid
    event loop conflicts between tests.

    Scope: function - new session for each test
    """
    # Create a fresh engine for this test to avoid event loop issues
    async_database_url = get_async_database_url(settings.POSTGRES_URL)
    engine = create_async_engine(
        async_database_url,
        echo=False,
        pool_pre_ping=True,
    )

    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        # Start a transaction
        async with session.begin():
            yield session
            # Rollback happens automatically when context exits
            await session.rollback()

    # Dispose of the engine after the test
    # Wrap in try/except to handle event loop closure during teardown
    try:
        await engine.dispose()
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise


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


# ============================================================================
# E2E Testing Fixtures for RSS Feeds and Scrapers (DEV-BE-69 Phase 6)
# ============================================================================


class LLMCallTracker:
    """Track LLM API calls to verify golden set bypass.

    Used in E2E tests to verify that:
    1. First query triggers LLM call
    2. Golden set retrieval does NOT trigger LLM call (cache hit)
    """

    def __init__(self):
        self.calls: list[dict] = []

    def record(self, query: str, response: str, model: str = "unknown"):
        """Record an LLM API call."""
        self.calls.append(
            {
                "query": query,
                "response": response,
                "model": model,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def reset(self):
        """Clear all recorded calls."""
        self.calls = []

    @property
    def call_count(self) -> int:
        """Number of LLM calls recorded."""
        return len(self.calls)

    def get_calls_for_query(self, query: str) -> list[dict]:
        """Get all calls that match a query (partial match)."""
        return [c for c in self.calls if query.lower() in c["query"].lower()]


@pytest.fixture
def llm_call_tracker():
    """Provide LLM call tracker for verifying golden set bypass.

    Usage:
        async def test_golden_set_bypass(llm_call_tracker):
            # First query - should call LLM
            response1 = await query_service.ask(query)
            assert llm_call_tracker.call_count == 1

            # Save as golden set
            await golden_set_service.save(query, response1)

            # Second query - should NOT call LLM (cache hit)
            llm_call_tracker.reset()
            response2 = await query_service.ask(query)
            assert llm_call_tracker.call_count == 0  # No new LLM call
    """
    return LLMCallTracker()


@pytest_asyncio.fixture
async def test_expert_profile(db_session: AsyncSession):
    """Create high-trust expert profile for auto-approval testing.

    This expert has:
    - High trust score (0.95) for auto-approval
    - All required specializations
    - Verified status

    Returns ExpertProfile object for use in tests.
    """
    from app.models.quality_analysis import ExpertProfile
    from app.models.user import User

    # First create a test user (required for foreign key constraint)
    test_user = User(
        id=99998,  # Use high ID to avoid conflicts
        email="test_expert_user@example.com",
        full_name="Test Expert User",
        hashed_password="$2b$12$test_hashed_password_placeholder",
        role="regular_user",
        is_active=True,
        email_verified=True,
        provider="email",
        created_at=datetime.utcnow(),
    )
    db_session.add(test_user)
    await db_session.flush()

    expert_id = uuid4()

    # Create expert profile with high trust
    expert = ExpertProfile(
        id=expert_id,
        user_id=test_user.id,  # Use the test user's ID
        trust_score=0.95,  # Auto-approve threshold
        is_verified=True,
        is_active=True,
        credentials=["Dottore Commercialista"],
        credential_types=["dottore_commercialista"],
        specializations=["fiscale", "tributario", "lavoro", "previdenza"],
        experience_years=10,
        feedback_count=0,
        feedback_accuracy_rate=1.0,
        average_response_time_seconds=60,
    )

    db_session.add(expert)
    await db_session.flush()

    yield expert

    # Cleanup handled by transaction rollback


@pytest.fixture
def rate_limit_delay():
    """Provide rate limiting delay for RSS feed tests.

    In CI/CD, we want to avoid hammering external RSS feeds.
    This fixture provides configurable delays between requests.

    Usage:
        async def test_feed(rate_limit_delay):
            await asyncio.sleep(rate_limit_delay)
            response = await fetch_feed(url)
    """
    # Use environment variable or default
    delay = float(os.environ.get("E2E_RATE_LIMIT_DELAY", "1.0"))
    return delay


@pytest.fixture
def e2e_test_config():
    """Provide E2E test configuration.

    Centralizes test configuration for consistency across tests.
    """
    return {
        "max_query_variations": 3,
        "semantic_similarity_threshold": 0.7,
        "bm25_min_results": 1,
        "golden_set_auto_approve_threshold": 0.9,
        "llm_timeout_seconds": 30,
        "rate_limit_between_feeds": 1.0,
    }


@pytest.fixture
def mock_llm_response():
    """Factory fixture for creating mock LLM responses.

    Useful for testing without actual LLM calls in unit tests,
    while E2E tests use real LLM calls.
    """

    def _create_response(content: str, tokens: int = 100):
        return {
            "content": content,
            "usage": {"prompt_tokens": 50, "completion_tokens": tokens},
            "model": "mock-model",
        }

    return _create_response


# ============================================================================
# Committed Session Fixture for Golden Set E2E Tests
# ============================================================================


@pytest_asyncio.fixture
async def db_session_committed() -> AsyncGenerator[AsyncSession, None]:
    """Create database session that COMMITS data for E2E tests.

    IMPORTANT: This fixture commits transactions, allowing the golden set
    workflow (which creates its own session) to see test data.

    Unlike db_session which rolls back, this fixture:
    1. Commits all changes during the test
    2. Tracks created entities for cleanup
    3. Deletes test data after the test completes

    Use this for full E2E flow tests that involve:
    - Golden set workflow (creates own session)
    - Expert feedback (foreign key to expert_profiles)
    - FAQ entries (cross-session visibility)

    CLEANUP: The fixture provides a cleanup helper via test_cleanup_ids dict.
    """
    async_database_url = get_async_database_url(settings.POSTGRES_URL)
    engine = create_async_engine(
        async_database_url,
        echo=False,
        pool_pre_ping=True,
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Track entities for cleanup
    cleanup_data = {
        "expert_profiles": [],
        "expert_feedback": [],
        "faq_entries": [],
        "faq_candidates": [],
        "knowledge_items": [],
    }

    async with async_session_maker() as session:
        # Attach cleanup tracker to session for use in tests
        session.cleanup_data = cleanup_data

        yield session

        # Commit any pending changes before cleanup
        try:
            await session.commit()
        except Exception:
            await session.rollback()

    # Cleanup in a new session (reverse order for FK constraints)
    async with async_session_maker() as cleanup_session:
        from sqlalchemy import text

        cleanup_order = [
            ("faq_entries", "id"),
            ("faq_candidates", "id"),
            ("expert_feedback", "id"),
            ("expert_profiles", "id"),
            ("knowledge_items", "id"),
            ('"user"', "id"),  # Clean up test users last (after dependent records)
        ]

        for table, id_col in cleanup_order:
            ids = cleanup_data.get(table, [])
            if ids:
                try:
                    # Use parameterized query for safety
                    placeholders = ", ".join([f":id_{i}" for i in range(len(ids))])
                    params = {f"id_{i}": str(id_val) for i, id_val in enumerate(ids)}
                    await cleanup_session.execute(
                        text(f"DELETE FROM {table} WHERE {id_col} IN ({placeholders})"),
                        params,
                    )
                except Exception as e:
                    print(f"Cleanup warning for {table}: {e}")

        try:
            await cleanup_session.commit()
        except Exception:
            await cleanup_session.rollback()

    # Dispose of the engine after the test
    # Wrap in try/except to handle event loop closure during teardown
    try:
        await engine.dispose()
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise


@pytest_asyncio.fixture
async def test_expert_profile_committed(db_session_committed: AsyncSession):
    """Create high-trust expert profile with committed transaction.

    Use this with db_session_committed for E2E tests that need
    the expert profile visible to the golden set workflow.
    """
    from app.models.quality_analysis import ExpertProfile
    from app.models.user import User

    # First create a test user (required for foreign key constraint)
    test_user = User(
        id=99997,  # Use high ID to avoid conflicts
        email="test_expert_committed_user@example.com",
        full_name="Test Expert Committed User",
        hashed_password="$2b$12$test_hashed_password_placeholder",
        role="regular_user",
        is_active=True,
        email_verified=True,
        provider="email",
        created_at=datetime.utcnow(),
    )
    db_session_committed.add(test_user)
    await db_session_committed.commit()

    # Track user for cleanup (key must match table name in cleanup_order)
    if '"user"' not in db_session_committed.cleanup_data:
        db_session_committed.cleanup_data['"user"'] = []
    db_session_committed.cleanup_data['"user"'].append(test_user.id)

    expert_id = uuid4()

    expert = ExpertProfile(
        id=expert_id,
        user_id=test_user.id,  # Use the test user's ID
        trust_score=0.95,
        is_verified=True,
        is_active=True,
        credentials=["Dottore Commercialista"],
        credential_types=["dottore_commercialista"],
        specializations=["fiscale", "tributario", "lavoro", "previdenza"],
        experience_years=10,
        feedback_count=0,
        feedback_accuracy_rate=1.0,
        average_response_time_seconds=60,
    )

    db_session_committed.add(expert)
    await db_session_committed.commit()

    # Track for cleanup
    db_session_committed.cleanup_data["expert_profiles"].append(expert_id)

    yield expert
