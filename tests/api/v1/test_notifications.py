"""DEV-424: Tests for Notification API Endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.notification import Notification, NotificationPriority, NotificationType


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def sample_notification(studio_id):
    return Notification(
        id=uuid4(),
        user_id=1,
        studio_id=studio_id,
        notification_type=NotificationType.SCADENZA,
        priority=NotificationPriority.HIGH,
        title="Scadenza IVA",
        is_read=False,
        dismissed=False,
    )


class TestListNotifications:
    """Test GET /notifications."""

    @pytest.mark.asyncio
    async def test_list_returns_200(self, studio_id, sample_notification) -> None:
        """Happy path: list notifications returns results."""
        from app.api.v1.notifications import NotificationResponse

        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.list_notifications = AsyncMock(return_value=[sample_notification])
            mock_db = AsyncMock()

            from app.api.v1.notifications import list_notifications

            result = await list_notifications(
                x_user_id=1,
                x_studio_id=studio_id,
                unread_only=False,
                offset=0,
                limit=50,
                db=mock_db,
            )
            assert len(result) == 1
            mock_svc.list_notifications.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_unread_filter(self, studio_id) -> None:
        """Unread filter passes to service."""
        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.list_notifications = AsyncMock(return_value=[])
            mock_db = AsyncMock()

            from app.api.v1.notifications import list_notifications

            await list_notifications(
                x_user_id=1,
                x_studio_id=studio_id,
                unread_only=True,
                offset=0,
                limit=50,
                db=mock_db,
            )
            mock_svc.list_notifications.assert_called_once_with(
                mock_db,
                user_id=1,
                studio_id=studio_id,
                unread_only=True,
                offset=0,
                limit=50,
            )

    @pytest.mark.asyncio
    async def test_list_empty(self, studio_id) -> None:
        """Edge case: empty list."""
        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.list_notifications = AsyncMock(return_value=[])
            mock_db = AsyncMock()

            from app.api.v1.notifications import list_notifications

            result = await list_notifications(
                x_user_id=1,
                x_studio_id=studio_id,
                unread_only=False,
                offset=0,
                limit=50,
                db=mock_db,
            )
            assert result == []


class TestUnreadCount:
    """Test GET /notifications/unread-count."""

    @pytest.mark.asyncio
    async def test_unread_count(self, studio_id) -> None:
        """Happy path: returns count."""
        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.get_unread_count = AsyncMock(return_value=5)
            mock_db = AsyncMock()

            from app.api.v1.notifications import get_unread_count

            result = await get_unread_count(
                x_user_id=1,
                x_studio_id=studio_id,
                db=mock_db,
            )
            assert result.count == 5


class TestMarkAsRead:
    """Test PUT /notifications/{id}/read."""

    @pytest.mark.asyncio
    async def test_mark_single_read(self, studio_id, sample_notification) -> None:
        """Happy path: mark notification as read."""
        sample_notification.is_read = True
        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.mark_as_read = AsyncMock(return_value=sample_notification)
            mock_db = AsyncMock()

            from app.api.v1.notifications import mark_as_read

            result = await mark_as_read(
                notification_id=sample_notification.id,
                x_user_id=1,
                x_studio_id=studio_id,
                db=mock_db,
            )
            assert result.is_read is True

    @pytest.mark.asyncio
    async def test_mark_read_not_found(self, studio_id) -> None:
        """404 when notification not found."""
        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.mark_as_read = AsyncMock(return_value=None)
            mock_db = AsyncMock()

            from app.api.v1.notifications import mark_as_read

            with pytest.raises(Exception) as exc_info:
                await mark_as_read(
                    notification_id=uuid4(),
                    x_user_id=1,
                    x_studio_id=studio_id,
                    db=mock_db,
                )
            assert exc_info.value.status_code == 404


class TestMarkAllRead:
    """Test PUT /notifications/mark-all-read."""

    @pytest.mark.asyncio
    async def test_mark_all_read(self, studio_id) -> None:
        """Happy path: bulk mark all read."""
        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.mark_all_as_read = AsyncMock(return_value=3)
            mock_db = AsyncMock()

            from app.api.v1.notifications import mark_all_as_read

            result = await mark_all_as_read(
                x_user_id=1,
                x_studio_id=studio_id,
                db=mock_db,
            )
            assert result.updated == 3


class TestDismissNotification:
    """Test DELETE /notifications/{id}."""

    @pytest.mark.asyncio
    async def test_dismiss_success(self, studio_id, sample_notification) -> None:
        """Happy path: dismiss notification."""
        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.dismiss_notification = AsyncMock(return_value=sample_notification)
            mock_db = AsyncMock()

            from app.api.v1.notifications import dismiss_notification

            await dismiss_notification(
                notification_id=sample_notification.id,
                x_user_id=1,
                x_studio_id=studio_id,
                db=mock_db,
            )
            mock_svc.dismiss_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_dismiss_not_found(self, studio_id) -> None:
        """404 when notification not found."""
        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.dismiss_notification = AsyncMock(return_value=None)
            mock_db = AsyncMock()

            from app.api.v1.notifications import dismiss_notification

            with pytest.raises(Exception) as exc_info:
                await dismiss_notification(
                    notification_id=uuid4(),
                    x_user_id=1,
                    x_studio_id=studio_id,
                    db=mock_db,
                )
            assert exc_info.value.status_code == 404
