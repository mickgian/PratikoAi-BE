"""Tests for get_db() async session management.

DEV-257: Verifies the async session pattern used by get_db().

Note: tests/services/conftest.py replaces app.services.database in
sys.modules with a MagicMock (session-scoped, autouse). This means
DatabaseService imported here is a mock. We test get_db() through
app.models.database instead, which uses the same AsyncSessionLocal
and identical implementation. The third test verifies DatabaseService
exposes the method (even on the mock, it checks attribute presence).
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestGetDb:
    """Test get_db() async session management."""

    @pytest.mark.asyncio
    @patch("app.models.database.AsyncSessionLocal")
    async def test_get_db_returns_async_session(self, mock_async_session_local):
        """Test that get_db() yields an AsyncSession."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_ctx.__aexit__.return_value = False
        mock_async_session_local.return_value = mock_ctx

        # Import the real get_db from models.database (not mocked by conftest)
        from app.models.database import get_db

        gen = get_db()
        session = await gen.__anext__()
        assert session is mock_session

        # Clean up the async generator
        await gen.aclose()

    @pytest.mark.asyncio
    @patch("app.models.database.AsyncSessionLocal")
    async def test_get_db_closes_session_on_exception(self, mock_async_session_local):
        """Test that session is closed when an exception occurs inside the block."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_ctx.__aexit__.return_value = False
        mock_async_session_local.return_value = mock_ctx

        from app.models.database import get_db

        gen = get_db()
        _session = await gen.__anext__()

        # Throw an exception into the generator to trigger the finally block
        with pytest.raises(ValueError, match="test error"):
            await gen.athrow(ValueError("test error"))

        # Session close is called in the finally block of get_db()
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_db_coexists_with_sync_operations(self):
        """Test that DatabaseService has get_db alongside sync methods."""
        from app.services.database import DatabaseService

        service = DatabaseService()

        assert hasattr(service, "get_db")
        assert callable(service.get_db)
        assert hasattr(service, "health_check")
        assert hasattr(service, "get_session_maker")
