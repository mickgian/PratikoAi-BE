"""Tests for DatabaseService.get_db() async context manager.

DEV-257: Fixes missing get_db() method that caused zero usage events
to be persisted, resulting in daily cost reports always showing €0.00.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.database import DatabaseService


class TestDatabaseServiceGetDb:
    """Test DatabaseService.get_db() async context manager."""

    @pytest.mark.asyncio
    @patch("app.services.database.AsyncSessionLocal")
    @patch("app.services.database.SQLModel")
    @patch("app.services.database.create_engine")
    @patch("app.services.database.settings")
    async def test_get_db_returns_async_session(
        self, mock_settings, mock_create_engine, mock_sqlmodel, mock_async_session_local
    ):
        """Test that get_db() yields an AsyncSession via async context manager."""
        mock_settings.POSTGRES_URL = "postgresql://user:pass@localhost/db"  # pragma: allowlist secret
        mock_settings.POSTGRES_POOL_SIZE = 10
        mock_settings.POSTGRES_MAX_OVERFLOW = 20
        mock_settings.ENVIRONMENT = MagicMock()
        mock_settings.ENVIRONMENT.value = "development"

        mock_session = AsyncMock(spec=AsyncSession)
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_async_session_local.return_value = mock_context

        service = DatabaseService()

        async with service.get_db() as db:
            assert db is mock_session

    @pytest.mark.asyncio
    @patch("app.services.database.AsyncSessionLocal")
    @patch("app.services.database.SQLModel")
    @patch("app.services.database.create_engine")
    @patch("app.services.database.settings")
    async def test_get_db_closes_session_on_exception(
        self, mock_settings, mock_create_engine, mock_sqlmodel, mock_async_session_local
    ):
        """Test that session is closed when an exception occurs inside the block."""
        mock_settings.POSTGRES_URL = "postgresql://user:pass@localhost/db"  # pragma: allowlist secret
        mock_settings.POSTGRES_POOL_SIZE = 10
        mock_settings.POSTGRES_MAX_OVERFLOW = 20
        mock_settings.ENVIRONMENT = MagicMock()
        mock_settings.ENVIRONMENT.value = "development"

        mock_session = AsyncMock(spec=AsyncSession)
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_async_session_local.return_value = mock_context

        service = DatabaseService()

        with pytest.raises(ValueError, match="test error"):
            async with service.get_db() as _db:
                raise ValueError("test error")

        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.services.database.SQLModel")
    @patch("app.services.database.create_engine")
    @patch("app.services.database.settings")
    async def test_get_db_coexists_with_sync_operations(self, mock_settings, mock_create_engine, mock_sqlmodel):
        """Test that adding get_db() does not break existing sync methods."""
        mock_settings.POSTGRES_URL = "postgresql://user:pass@localhost/db"  # pragma: allowlist secret
        mock_settings.POSTGRES_POOL_SIZE = 10
        mock_settings.POSTGRES_MAX_OVERFLOW = 20
        mock_settings.ENVIRONMENT = MagicMock()
        mock_settings.ENVIRONMENT.value = "development"

        service = DatabaseService()

        assert hasattr(service, "get_db")
        assert callable(service.get_db)
        assert hasattr(service, "health_check")
        assert hasattr(service, "get_session_maker")
