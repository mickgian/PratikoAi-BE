"""DEV-438: DeadlineReminderService — CRUD for per-deadline user reminders."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.deadline_reminder import DeadlineReminder


class DeadlineReminderService:
    """Service for custom per-deadline user reminders."""

    async def set_reminder(
        self,
        db: AsyncSession,
        *,
        deadline_id: UUID,
        user_id: int,
        studio_id: UUID,
        remind_at: datetime,
    ) -> DeadlineReminder:
        """Create or update a reminder (upsert). Rejects past remind_at."""
        if remind_at <= datetime.now(UTC):
            raise ValueError("La data del promemoria deve essere nel futuro.")

        # Upsert: find existing or create new
        existing = await self._get_reminder(db, deadline_id=deadline_id, user_id=user_id, studio_id=studio_id)

        if existing is not None:
            existing.remind_at = remind_at
            existing.is_active = True
            existing.notification_sent = False
            await db.flush()
            logger.info("deadline_reminder_updated", deadline_id=str(deadline_id), user_id=user_id)
            return existing

        reminder = DeadlineReminder(
            deadline_id=deadline_id,
            user_id=user_id,
            studio_id=studio_id,
            remind_at=remind_at,
        )
        db.add(reminder)
        await db.flush()

        logger.info("deadline_reminder_created", deadline_id=str(deadline_id), user_id=user_id)
        return reminder

    async def delete_reminder(
        self,
        db: AsyncSession,
        *,
        deadline_id: UUID,
        user_id: int,
        studio_id: UUID,
    ) -> bool:
        """Delete a reminder. Returns True if deleted, False if not found."""
        reminder = await self._get_reminder(db, deadline_id=deadline_id, user_id=user_id, studio_id=studio_id)
        if reminder is None:
            return False

        await db.delete(reminder)
        await db.flush()
        logger.info("deadline_reminder_deleted", deadline_id=str(deadline_id), user_id=user_id)
        return True

    async def get_reminder(
        self,
        db: AsyncSession,
        *,
        deadline_id: UUID,
        user_id: int,
        studio_id: UUID,
    ) -> DeadlineReminder | None:
        """Get reminder for a user-deadline pair."""
        return await self._get_reminder(db, deadline_id=deadline_id, user_id=user_id, studio_id=studio_id)

    async def _get_reminder(
        self,
        db: AsyncSession,
        *,
        deadline_id: UUID,
        user_id: int,
        studio_id: UUID,
    ) -> DeadlineReminder | None:
        """Internal: fetch with tenant isolation."""
        result = await db.execute(
            select(DeadlineReminder).where(
                and_(
                    DeadlineReminder.deadline_id == deadline_id,
                    DeadlineReminder.user_id == user_id,
                    DeadlineReminder.studio_id == studio_id,
                )
            )
        )
        return result.scalar_one_or_none()


deadline_reminder_service = DeadlineReminderService()
