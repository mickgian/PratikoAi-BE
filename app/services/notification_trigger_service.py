"""DEV-425: Notification Creation Triggers — Fire-and-forget notification wiring.

Wires notification creation into existing services. Parent operations never fail
due to notification errors. Deduplicates triggers within a 1-hour window.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.notification import Notification, NotificationPriority, NotificationType

DEDUP_WINDOW_HOURS = 1


class NotificationTriggerService:
    """Fire-and-forget notification triggers for system events."""

    async def trigger_scadenza(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
        deadline_title: str,
        reference_id: UUID | None = None,
    ) -> None:
        """Trigger SCADENZA notification when deadline is within threshold."""
        await self._safe_create(
            db,
            user_id=user_id,
            studio_id=studio_id,
            notification_type=NotificationType.SCADENZA,
            priority=NotificationPriority.HIGH,
            title=f"Scadenza in arrivo: {deadline_title}",
            reference_id=reference_id,
            reference_type="deadline",
        )

    async def trigger_match(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
        match_description: str,
        reference_id: UUID | None = None,
    ) -> None:
        """Trigger MATCH notification on new normative match."""
        await self._safe_create(
            db,
            user_id=user_id,
            studio_id=studio_id,
            notification_type=NotificationType.MATCH,
            priority=NotificationPriority.MEDIUM,
            title=f"Nuovo match normativo: {match_description}",
            reference_id=reference_id,
            reference_type="match",
        )

    async def trigger_comunicazione(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
        communication_title: str,
        reference_id: UUID | None = None,
    ) -> None:
        """Trigger COMUNICAZIONE notification on approval."""
        await self._safe_create(
            db,
            user_id=user_id,
            studio_id=studio_id,
            notification_type=NotificationType.COMUNICAZIONE,
            priority=NotificationPriority.LOW,
            title=f"Comunicazione approvata: {communication_title}",
            reference_id=reference_id,
            reference_type="communication",
        )

    async def trigger_normativa(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
        regulation_title: str,
        reference_id: UUID | None = None,
    ) -> None:
        """Trigger NORMATIVA notification on regulation update."""
        await self._safe_create(
            db,
            user_id=user_id,
            studio_id=studio_id,
            notification_type=NotificationType.NORMATIVA,
            priority=NotificationPriority.MEDIUM,
            title=f"Aggiornamento normativo: {regulation_title}",
            reference_id=reference_id,
            reference_type="regulation",
        )

    async def _safe_create(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
        notification_type: NotificationType,
        priority: NotificationPriority,
        title: str,
        reference_id: UUID | None = None,
        reference_type: str | None = None,
    ) -> None:
        """Fire-and-forget notification creation with deduplication."""
        try:
            if await self._is_duplicate(
                db,
                user_id=user_id,
                studio_id=studio_id,
                notification_type=notification_type,
                reference_id=reference_id,
            ):
                logger.info(
                    "notification_trigger_deduplicated",
                    notification_type=notification_type.value,
                    reference_id=str(reference_id) if reference_id else None,
                )
                return

            from app.services.notification_service import notification_service

            await notification_service.create_notification(
                db,
                user_id=user_id,
                studio_id=studio_id,
                notification_type=notification_type,
                priority=priority,
                title=title,
                reference_id=reference_id,
                reference_type=reference_type,
            )
        except Exception as e:
            # Fire-and-forget: never let notification errors propagate
            logger.warning(
                "notification_trigger_failed",
                notification_type=notification_type.value,
                error_type=type(e).__name__,
                error_message=str(e),
            )

    async def _is_duplicate(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
        notification_type: NotificationType,
        reference_id: UUID | None,
    ) -> bool:
        """Check for duplicate notification within dedup window."""
        if reference_id is None:
            return False

        cutoff = datetime.now(UTC) - timedelta(hours=DEDUP_WINDOW_HOURS)
        result = await db.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.studio_id == studio_id,
                    Notification.notification_type == notification_type,
                    Notification.reference_id == reference_id,
                    Notification.created_at >= cutoff,
                )
            )
        )
        count = result.scalar_one_or_none() or 0
        return count > 0


notification_trigger_service = NotificationTriggerService()
