"""DEV-425: Tests for Notification Creation Triggers."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.notification_trigger_service import NotificationTriggerService


@pytest.fixture
def svc() -> NotificationTriggerService:
    return NotificationTriggerService()


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def studio_id():
    return uuid4()


class TestTriggerScadenza:
    """Test SCADENZA notification trigger."""

    @pytest.mark.asyncio
    async def test_creates_notification(self, svc, mock_db, studio_id) -> None:
        """Happy path: creates SCADENZA notification."""
        with patch.object(svc, "_is_duplicate", return_value=False):
            with patch("app.services.notification_service.notification_service") as mock_notif:
                mock_notif.create_notification = AsyncMock()
                await svc.trigger_scadenza(
                    mock_db,
                    user_id=1,
                    studio_id=studio_id,
                    deadline_title="IVA trimestrale",
                    reference_id=uuid4(),
                )
                mock_notif.create_notification.assert_called_once()


class TestTriggerMatch:
    """Test MATCH notification trigger."""

    @pytest.mark.asyncio
    async def test_creates_notification(self, svc, mock_db, studio_id) -> None:
        """Happy path: creates MATCH notification."""
        with patch.object(svc, "_is_duplicate", return_value=False):
            with patch("app.services.notification_service.notification_service") as mock_notif:
                mock_notif.create_notification = AsyncMock()
                await svc.trigger_match(
                    mock_db,
                    user_id=1,
                    studio_id=studio_id,
                    match_description="Nuova normativa rilevante",
                )
                mock_notif.create_notification.assert_called_once()


class TestTriggerComunicazione:
    """Test COMUNICAZIONE notification trigger."""

    @pytest.mark.asyncio
    async def test_creates_notification(self, svc, mock_db, studio_id) -> None:
        """Happy path: creates COMUNICAZIONE notification."""
        with patch.object(svc, "_is_duplicate", return_value=False):
            with patch("app.services.notification_service.notification_service") as mock_notif:
                mock_notif.create_notification = AsyncMock()
                await svc.trigger_comunicazione(
                    mock_db,
                    user_id=1,
                    studio_id=studio_id,
                    communication_title="Lettera cliente",
                )
                mock_notif.create_notification.assert_called_once()


class TestTriggerNormativa:
    """Test NORMATIVA notification trigger."""

    @pytest.mark.asyncio
    async def test_creates_notification(self, svc, mock_db, studio_id) -> None:
        """Happy path: creates NORMATIVA notification."""
        with patch.object(svc, "_is_duplicate", return_value=False):
            with patch("app.services.notification_service.notification_service") as mock_notif:
                mock_notif.create_notification = AsyncMock()
                await svc.trigger_normativa(
                    mock_db,
                    user_id=1,
                    studio_id=studio_id,
                    regulation_title="DL 123/2026",
                )
                mock_notif.create_notification.assert_called_once()


class TestFireAndForget:
    """Test fire-and-forget: parent operation never fails."""

    @pytest.mark.asyncio
    async def test_notification_error_swallowed(self, svc, mock_db, studio_id) -> None:
        """Notification creation failure doesn't propagate."""
        with patch.object(svc, "_is_duplicate", return_value=False):
            with patch("app.services.notification_service.notification_service") as mock_notif:
                mock_notif.create_notification = AsyncMock(side_effect=Exception("DB error"))
                # Should NOT raise
                await svc.trigger_scadenza(
                    mock_db,
                    user_id=1,
                    studio_id=studio_id,
                    deadline_title="IVA",
                )


class TestDeduplication:
    """Test deduplication within 1-hour window."""

    @pytest.mark.asyncio
    async def test_duplicate_skipped(self, svc, mock_db, studio_id) -> None:
        """Duplicate within window is skipped."""
        with patch.object(svc, "_is_duplicate", return_value=True):
            with patch("app.services.notification_service.notification_service") as mock_notif:
                mock_notif.create_notification = AsyncMock()
                await svc.trigger_scadenza(
                    mock_db,
                    user_id=1,
                    studio_id=studio_id,
                    deadline_title="IVA",
                    reference_id=uuid4(),
                )
                mock_notif.create_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_reference_no_dedup(self, svc, mock_db, studio_id) -> None:
        """No reference_id skips dedup check."""
        result = await svc._is_duplicate(
            mock_db,
            user_id=1,
            studio_id=studio_id,
            notification_type=MagicMock(),
            reference_id=None,
        )
        assert result is False
