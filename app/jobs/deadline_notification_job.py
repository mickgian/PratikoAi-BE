"""DEV-384: Deadline Notification Background Job -- Daily notifications for upcoming deadlines.

Sends notifications at configurable intervals: 30 days, 7 days, 1 day before deadline.
Skips deadlines where all client-deadline associations are already completed.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.notification import NotificationPriority, NotificationType
from app.services.deadline_service import deadline_service
from app.services.notification_service import notification_service

DEFAULT_INTERVALS = [30, 7, 1]


@dataclass
class DeadlineNotificationResult:
    """Result summary of a deadline notification job run."""

    deadlines_checked: int
    notifications_sent: int
    errors: int


async def run_deadline_notifications(
    db: AsyncSession,
    studio_id: UUID,
    user_id: int,
    intervals: list[int] | None = None,
) -> DeadlineNotificationResult:
    """Send notifications for upcoming deadlines at each configured interval.

    Args:
        db: Async database session.
        studio_id: Studio UUID for multi-tenant isolation.
        user_id: User ID for notification recipient.
        intervals: Days-before-deadline intervals to check. Defaults to [30, 7, 1].

    Returns:
        DeadlineNotificationResult with counters for checked deadlines,
        sent notifications, and errors.
    """
    if intervals is None:
        intervals = DEFAULT_INTERVALS

    logger.info(
        "deadline_notification_job_started",
        studio_id=str(studio_id),
        user_id=user_id,
        intervals=intervals,
    )

    deadlines_checked = 0
    notifications_sent = 0
    errors = 0

    for days_ahead in intervals:
        upcoming = await deadline_service.list_upcoming(db, days_ahead=days_ahead)

        for deadline in upcoming:
            deadlines_checked += 1

            if await _all_client_deadlines_completed(db, studio_id, deadline.id):
                continue

            sent = await _send_deadline_notification(
                db=db,
                studio_id=studio_id,
                user_id=user_id,
                deadline=deadline,
                days_ahead=days_ahead,
            )
            if sent:
                notifications_sent += 1
            else:
                errors += 1

    logger.info(
        "deadline_notification_job_completed",
        studio_id=str(studio_id),
        user_id=user_id,
        deadlines_checked=deadlines_checked,
        notifications_sent=notifications_sent,
        errors=errors,
    )

    return DeadlineNotificationResult(
        deadlines_checked=deadlines_checked,
        notifications_sent=notifications_sent,
        errors=errors,
    )


async def _all_client_deadlines_completed(
    db: AsyncSession,
    studio_id: UUID,
    deadline_id: UUID,
) -> bool:
    """Check if all client-deadline associations for this deadline are completed.

    Returns False if there are no client-deadline associations (general deadline
    still needs a notification) or if any association is incomplete.
    """
    client_deadlines = await deadline_service.list_by_studio(db, studio_id=studio_id)

    # Filter to only client-deadlines referencing this specific deadline
    relevant = [cd for cd in client_deadlines if cd.deadline_id == deadline_id]

    if not relevant:
        # No client-deadline associations -- still send a general notification
        return False

    return all(cd.is_completed for cd in relevant)


async def _send_deadline_notification(
    db: AsyncSession,
    studio_id: UUID,
    user_id: int,
    deadline: object,
    days_ahead: int,
) -> bool:
    """Fire-and-forget notification for an upcoming deadline. Returns True on success."""
    try:
        priority = _priority_for_interval(days_ahead)

        await notification_service.create_notification(
            db=db,
            user_id=user_id,
            studio_id=studio_id,
            notification_type=NotificationType.SCADENZA,
            priority=priority,
            title=f"Scadenza tra {days_ahead} giorni: {deadline.title}",
            description=deadline.description,
            reference_id=deadline.id,
            reference_type="deadline",
        )
        return True
    except Exception as exc:
        logger.warning(
            "deadline_notification_error",
            deadline_id=str(deadline.id),
            deadline_title=deadline.title,
            days_ahead=days_ahead,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        return False


def _priority_for_interval(days_ahead: int) -> NotificationPriority:
    """Determine notification priority based on how soon the deadline is."""
    if days_ahead <= 1:
        return NotificationPriority.URGENT
    if days_ahead <= 7:
        return NotificationPriority.HIGH
    return NotificationPriority.MEDIUM
