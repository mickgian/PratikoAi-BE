"""DEV-375: Breach Notification Service — GDPR breach lifecycle management.

Detection → assessment → notification within 72 hours.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.breach_notification import BreachNotification, BreachSeverity, BreachStatus

# Valid status transitions
_VALID_TRANSITIONS: dict[BreachStatus, set[BreachStatus]] = {
    BreachStatus.DETECTED: {BreachStatus.INVESTIGATING},
    BreachStatus.INVESTIGATING: {BreachStatus.CONTAINED},
    BreachStatus.CONTAINED: {BreachStatus.AUTHORITY_NOTIFIED, BreachStatus.RESOLVED},
    BreachStatus.AUTHORITY_NOTIFIED: {BreachStatus.RESOLVED},
    BreachStatus.RESOLVED: set(),
}


class BreachNotificationService:
    """Service for GDPR breach lifecycle management."""

    async def create(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        title: str,
        description: str,
        severity: BreachSeverity,
        reported_by: int,
        affected_records_count: int | None = None,
        data_categories: list | None = None,
    ) -> BreachNotification:
        """Report a new data breach."""
        breach = BreachNotification(
            studio_id=studio_id,
            title=title,
            description=description,
            severity=severity,
            reported_by=reported_by,
            affected_records_count=affected_records_count,
            data_categories=data_categories,
        )
        db.add(breach)
        await db.flush()

        logger.info(
            "breach_reported",
            breach_id=str(breach.id),
            studio_id=str(studio_id),
            severity=severity.value,
        )
        return breach

    async def get_by_id(self, db: AsyncSession, *, breach_id: UUID, studio_id: UUID) -> BreachNotification | None:
        """Get breach by ID within studio."""
        result = await db.execute(
            select(BreachNotification).where(
                and_(
                    BreachNotification.id == breach_id,
                    BreachNotification.studio_id == studio_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        db: AsyncSession,
        *,
        breach_id: UUID,
        studio_id: UUID,
        new_status: BreachStatus,
    ) -> BreachNotification | None:
        """Transition breach to new status.

        Raises ValueError if transition is not valid.
        """
        breach = await self.get_by_id(db, breach_id=breach_id, studio_id=studio_id)
        if breach is None:
            return None

        self._validate_transition(breach.status, new_status)

        breach.status = new_status

        if new_status == BreachStatus.AUTHORITY_NOTIFIED:
            breach.authority_notified_at = datetime.now(UTC)
        elif new_status == BreachStatus.RESOLVED:
            breach.resolved_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "breach_status_updated",
            breach_id=str(breach_id),
            new_status=new_status.value,
        )
        return breach

    async def list_by_studio(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        status: BreachStatus | None = None,
    ) -> list[BreachNotification]:
        """List breaches for a studio."""
        query = select(BreachNotification).where(BreachNotification.studio_id == studio_id)
        if status is not None:
            query = query.where(BreachNotification.status == status)
        query = query.order_by(BreachNotification.detected_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    async def check_overdue_notifications(
        self,
        db: AsyncSession,
    ) -> list[BreachNotification]:
        """Find breaches past 72h deadline without authority notification."""
        cutoff = datetime.now(UTC) - timedelta(hours=72)

        result = await db.execute(
            select(BreachNotification).where(
                and_(
                    BreachNotification.authority_notified_at.is_(None),
                    BreachNotification.resolved_at.is_(None),
                    BreachNotification.detected_at <= cutoff,
                    BreachNotification.status != BreachStatus.RESOLVED,
                )
            )
        )
        overdue = list(result.scalars().all())

        if overdue:
            logger.warning(
                "breach_overdue_notifications",
                count=len(overdue),
                breach_ids=[str(b.id) for b in overdue],
            )

        return overdue

    @staticmethod
    def _validate_transition(current: BreachStatus, target: BreachStatus) -> None:
        """Raise ValueError if transition is not allowed."""
        allowed = _VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(f"La transizione da '{current.value}' a '{target.value}' non è valida.")


breach_notification_service = BreachNotificationService()
