"""DEV-441: Tests for Settings API."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def studio_id():
    return uuid4()


class TestGetSettings:
    """Test GET /settings."""

    @pytest.mark.asyncio
    async def test_get_settings_200(self, studio_id) -> None:
        """Happy path: returns settings with defaults."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.api.v1.settings import get_settings

        result = await get_settings(x_studio_id=studio_id, db=mock_db)
        assert result.studio_id == studio_id
        assert result.notification_preferences["scadenza"] is True
        assert result.display_preferences["language"] == "it"

    @pytest.mark.asyncio
    async def test_get_settings_with_stored_prefs(self, studio_id) -> None:
        """Returns stored preferences when they exist."""
        mock_studio = SimpleNamespace(
            id=studio_id,
            settings={
                "notification_preferences": {
                    "scadenza": False,
                    "match": True,
                    "comunicazione": True,
                    "normativa": False,
                },
                "display_preferences": {"theme": "dark", "language": "it", "items_per_page": 50},
            },
        )
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_studio
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.api.v1.settings import get_settings

        result = await get_settings(x_studio_id=studio_id, db=mock_db)
        assert result.notification_preferences["scadenza"] is False
        assert result.display_preferences["theme"] == "dark"


class TestUpdateSettings:
    """Test PUT /settings."""

    @pytest.mark.asyncio
    async def test_update_settings_200(self, studio_id) -> None:
        """Happy path: update notification prefs."""
        mock_studio = SimpleNamespace(
            id=studio_id,
            settings={},
        )
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_studio
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        from app.api.v1.settings import SettingsUpdateRequest, update_settings

        body = SettingsUpdateRequest(
            notification_preferences={"scadenza": False, "match": True, "comunicazione": True, "normativa": True},
        )
        result = await update_settings(body=body, x_studio_id=studio_id, db=mock_db)
        assert result.notification_preferences["scadenza"] is False

    @pytest.mark.asyncio
    async def test_update_studio_not_found(self, studio_id) -> None:
        """Studio not found returns 404."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.api.v1.settings import SettingsUpdateRequest, update_settings

        body = SettingsUpdateRequest(notification_preferences={"scadenza": False})

        with pytest.raises(Exception) as exc_info:
            await update_settings(body=body, x_studio_id=studio_id, db=mock_db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_display_prefs(self, studio_id) -> None:
        """Update display preferences."""
        mock_studio = SimpleNamespace(id=studio_id, settings={})
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_studio
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        from app.api.v1.settings import SettingsUpdateRequest, update_settings

        body = SettingsUpdateRequest(
            display_preferences={"theme": "dark", "language": "it", "items_per_page": 100},
        )
        result = await update_settings(body=body, x_studio_id=studio_id, db=mock_db)
        assert result.display_preferences["theme"] == "dark"
