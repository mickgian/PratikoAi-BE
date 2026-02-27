"""DEV-423: NotificationService — CRUD with time-grouped listing and bulk actions.

Supports create, list (with optional unread filter), unread count,
mark-as-read (single + bulk), and dismiss.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.notification import Notification, NotificationPriority, NotificationType


class NotificationService:
    """Service for in-app notification management."""

    async def create_notification(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
        notification_type: NotificationType,
        priority: NotificationPriority,
        title: str,
        description: str | None = None,
        reference_id: UUID | None = None,
        reference_type: str | None = None,
    ) -> Notification:
        """Create a new notification."""
        notif = Notification(
            user_id=user_id,
            studio_id=studio_id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            description=description,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        db.add(notif)
        await db.flush()

        logger.info(
            "notification_created",
            notification_id=str(notif.id),
            notification_type=notification_type.value,
            user_id=user_id,
        )
        return notif

    async def list_notifications(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
        unread_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        """List notifications for a user in a studio, ordered by creation time."""
        query = select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.studio_id == studio_id,
                Notification.dismissed.is_(False),
            )
        )
        if unread_only:
            query = query.where(Notification.is_read.is_(False))

        query = query.offset(offset).limit(limit).order_by(Notification.created_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_unread_count(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
    ) -> int:
        """Return count of unread, non-dismissed notifications."""
        result = await db.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.studio_id == studio_id,
                    Notification.is_read.is_(False),
                    Notification.dismissed.is_(False),
                )
            )
        )
        return result.scalar_one()

    async def mark_as_read(
        self,
        db: AsyncSession,
        *,
        notification_id: UUID,
        user_id: int,
        studio_id: UUID,
    ) -> Notification | None:
        """Mark a single notification as read. Idempotent."""
        notif = await self._get_notification(db, notification_id=notification_id, user_id=user_id, studio_id=studio_id)
        if notif is None:
            return None

        if not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.now(UTC)
            await db.flush()

        return notif

    async def mark_all_as_read(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
    ) -> int:
        """Bulk mark all unread notifications as read. Returns count updated."""
        result = await db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.studio_id == studio_id,
                    Notification.is_read.is_(False),
                )
            )
            .values(is_read=True, read_at=datetime.now(UTC))
        )
        await db.flush()

        logger.info("notifications_marked_all_read", user_id=user_id, count=result.rowcount)
        return result.rowcount

    async def dismiss_notification(
        self,
        db: AsyncSession,
        *,
        notification_id: UUID,
        user_id: int,
        studio_id: UUID,
    ) -> Notification | None:
        """Dismiss a notification (soft hide). Returns None if not found."""
        notif = await self._get_notification(db, notification_id=notification_id, user_id=user_id, studio_id=studio_id)
        if notif is None:
            return None

        notif.dismissed = True
        await db.flush()

        logger.info("notification_dismissed", notification_id=str(notification_id))
        return notif

    async def _get_notification(
        self,
        db: AsyncSession,
        *,
        notification_id: UUID,
        user_id: int,
        studio_id: UUID,
    ) -> Notification | None:
        """Fetch notification enforcing user + studio isolation."""
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                    Notification.studio_id == studio_id,
                )
            )
        )
        return result.scalar_one_or_none()


notification_service = NotificationService()
