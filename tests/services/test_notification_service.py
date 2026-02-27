"""DEV-423: Tests for NotificationService CRUD."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.notification import Notification, NotificationPriority, NotificationType
from app.services.notification_service import NotificationService


@pytest.fixture
def svc() -> NotificationService:
    return NotificationService()


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def studio_id():
    return uuid4()


class TestCreateNotification:
    """Test NotificationService.create_notification()."""

    @pytest.mark.asyncio
    async def test_create_success(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Happy path: create a notification."""
        result = await svc.create_notification(
            db=mock_db,
            user_id=1,
            studio_id=studio_id,
            notification_type=NotificationType.SCADENZA,
            priority=NotificationPriority.HIGH,
            title="Scadenza IVA in arrivo",
            description="La scadenza IVA è il 16 marzo.",
        )
        assert result.notification_type == NotificationType.SCADENZA
        assert result.title == "Scadenza IVA in arrivo"
        assert result.is_read is False
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_reference(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Create notification with polymorphic reference."""
        ref_id = uuid4()
        result = await svc.create_notification(
            db=mock_db,
            user_id=1,
            studio_id=studio_id,
            notification_type=NotificationType.MATCH,
            priority=NotificationPriority.MEDIUM,
            title="Nuovo match",
            reference_id=ref_id,
            reference_type="proactive_suggestion",
        )
        assert result.reference_id == ref_id
        assert result.reference_type == "proactive_suggestion"

    @pytest.mark.asyncio
    async def test_create_no_description(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Edge case: create without description."""
        result = await svc.create_notification(
            db=mock_db,
            user_id=1,
            studio_id=studio_id,
            notification_type=NotificationType.NORMATIVA,
            priority=NotificationPriority.LOW,
            title="Test",
        )
        assert result.description is None


class TestGetUnreadCount:
    """Test NotificationService.get_unread_count()."""

    @pytest.mark.asyncio
    async def test_unread_count(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Returns count of unread notifications."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await svc.get_unread_count(db=mock_db, user_id=1, studio_id=studio_id)
        assert count == 5

    @pytest.mark.asyncio
    async def test_unread_count_zero(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Edge case: no unread notifications."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await svc.get_unread_count(db=mock_db, user_id=1, studio_id=studio_id)
        assert count == 0


class TestMarkAsRead:
    """Test NotificationService.mark_as_read()."""

    @pytest.mark.asyncio
    async def test_mark_as_read_success(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Happy path: mark notification as read."""
        notif = Notification(
            id=uuid4(),
            user_id=1,
            studio_id=studio_id,
            notification_type=NotificationType.SCADENZA,
            priority=NotificationPriority.HIGH,
            title="Test",
            is_read=False,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = notif
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.mark_as_read(db=mock_db, notification_id=notif.id, user_id=1, studio_id=studio_id)
        assert result is not None
        assert result.is_read is True
        assert result.read_at is not None

    @pytest.mark.asyncio
    async def test_mark_as_read_not_found(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Not found returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.mark_as_read(db=mock_db, notification_id=uuid4(), user_id=1, studio_id=studio_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_mark_as_read_idempotent(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Idempotent: already-read notification stays read."""
        read_at = datetime.now(UTC)
        notif = Notification(
            id=uuid4(),
            user_id=1,
            studio_id=studio_id,
            notification_type=NotificationType.MATCH,
            priority=NotificationPriority.LOW,
            title="Test",
            is_read=True,
        )
        # Manually set read_at since model doesn't auto-set
        notif.read_at = read_at
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = notif
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.mark_as_read(db=mock_db, notification_id=notif.id, user_id=1, studio_id=studio_id)
        assert result is not None
        assert result.is_read is True
        assert result.read_at == read_at


class TestDismissNotification:
    """Test NotificationService.dismiss_notification()."""

    @pytest.mark.asyncio
    async def test_dismiss_success(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Happy path: dismiss notification."""
        notif = Notification(
            id=uuid4(),
            user_id=1,
            studio_id=studio_id,
            notification_type=NotificationType.COMUNICAZIONE,
            priority=NotificationPriority.LOW,
            title="Test",
            dismissed=False,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = notif
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.dismiss_notification(db=mock_db, notification_id=notif.id, user_id=1, studio_id=studio_id)
        assert result is not None
        assert result.dismissed is True

    @pytest.mark.asyncio
    async def test_dismiss_not_found(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Not found returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.dismiss_notification(db=mock_db, notification_id=uuid4(), user_id=1, studio_id=studio_id)
        assert result is None


class TestListNotifications:
    """Test NotificationService.list_notifications()."""

    @pytest.mark.asyncio
    async def test_list_empty(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Edge case: empty list."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.list_notifications(db=mock_db, user_id=1, studio_id=studio_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_with_notifications(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Happy path: list notifications."""
        notifs = [
            Notification(
                user_id=1,
                studio_id=studio_id,
                notification_type=NotificationType.SCADENZA,
                priority=NotificationPriority.HIGH,
                title="Test 1",
            ),
            Notification(
                user_id=1,
                studio_id=studio_id,
                notification_type=NotificationType.MATCH,
                priority=NotificationPriority.LOW,
                title="Test 2",
            ),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = notifs
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.list_notifications(db=mock_db, user_id=1, studio_id=studio_id)
        assert len(result) == 2


class TestMarkAllAsRead:
    """Test NotificationService.mark_all_as_read()."""

    @pytest.mark.asyncio
    async def test_mark_all_as_read(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Bulk mark all as read returns count."""
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await svc.mark_all_as_read(db=mock_db, user_id=1, studio_id=studio_id)
        assert count == 3

    @pytest.mark.asyncio
    async def test_mark_all_as_read_none(self, svc: NotificationService, mock_db: AsyncMock, studio_id) -> None:
        """Edge case: no unread notifications to mark."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await svc.mark_all_as_read(db=mock_db, user_id=1, studio_id=studio_id)
        assert count == 0
