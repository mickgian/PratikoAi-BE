"""DEV-325: Background Matching Job — Primary proactive matching delivery.

Triggered by: (1) RSS/KB ingestion, (2) chat normative response.
Creates ProactiveSuggestion + MATCH notifications via NotificationService.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.matching_rule import MatchingRule
from app.models.notification import NotificationPriority, NotificationType
from app.models.proactive_suggestion import ProactiveSuggestion
from app.services.normative_matching_service import normative_matching_service
from app.services.notification_service import notification_service


@dataclass
class MatchingJobResult:
    """Result summary of a background matching job run."""

    rules_processed: int
    matches_found: int
    suggestions_created: int
    notifications_sent: int


async def run_matching_job(
    db: AsyncSession,
    studio_id: UUID,
    knowledge_item_id: int | None = None,
    trigger: str = "rss",
) -> MatchingJobResult:
    """Execute background matching: rules -> clients -> suggestions -> notifications.

    Args:
        db: Async database session.
        studio_id: Studio UUID for multi-tenant isolation.
        knowledge_item_id: Optional FK to the knowledge item that triggered matching.
        trigger: Origin of the job ("rss" or "chat").

    Returns:
        MatchingJobResult with counters for processed rules, matches, suggestions,
        and notifications.
    """
    logger.info(
        "matching_job_started",
        studio_id=str(studio_id),
        knowledge_item_id=knowledge_item_id,
        trigger=trigger,
    )

    rules = await _fetch_active_rules(db)

    rules_processed = 0
    matches_found = 0
    suggestions_created = 0
    notifications_sent = 0

    for rule in rules:
        rules_processed += 1

        try:
            matches = await normative_matching_service.match_rule_to_clients(
                db,
                rule_id=rule.id,
                studio_id=studio_id,
            )
        except Exception as exc:
            logger.error(
                "matching_job_rule_error",
                rule_id=str(rule.id),
                rule_name=rule.name,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            continue

        if not matches:
            continue

        matches_found += len(matches)

        for match in matches:
            suggestion = _build_suggestion(
                studio_id=studio_id,
                knowledge_item_id=knowledge_item_id or 0,
                match=match,
                rule=rule,
            )
            db.add(suggestion)
            suggestions_created += 1

            sent = await _send_notification(
                db=db,
                studio_id=studio_id,
                match=match,
                rule=rule,
                suggestion=suggestion,
            )
            if sent:
                notifications_sent += 1

    await db.flush()

    logger.info(
        "matching_job_completed",
        studio_id=str(studio_id),
        trigger=trigger,
        rules_processed=rules_processed,
        matches_found=matches_found,
        suggestions_created=suggestions_created,
        notifications_sent=notifications_sent,
    )

    return MatchingJobResult(
        rules_processed=rules_processed,
        matches_found=matches_found,
        suggestions_created=suggestions_created,
        notifications_sent=notifications_sent,
    )


async def _fetch_active_rules(db: AsyncSession) -> list[MatchingRule]:
    """Fetch all currently active matching rules."""
    result = await db.execute(
        select(MatchingRule).where(
            and_(
                MatchingRule.is_active.is_(True),
            )
        )
    )
    return list(result.scalars().all())


def _build_suggestion(
    studio_id: UUID,
    knowledge_item_id: int,
    match: dict,
    rule: MatchingRule,
) -> ProactiveSuggestion:
    """Build a ProactiveSuggestion from a rule match result."""
    return ProactiveSuggestion(
        studio_id=studio_id,
        knowledge_item_id=knowledge_item_id,
        matched_client_ids=[match["client_id"]],
        match_score=match["score"],
        suggestion_text=f"{rule.name}: {rule.description}",
    )


async def _send_notification(
    db: AsyncSession,
    studio_id: UUID,
    match: dict,
    rule: MatchingRule,
    suggestion: ProactiveSuggestion,
) -> bool:
    """Fire-and-forget notification for a match. Returns True on success."""
    try:
        await notification_service.create_notification(
            db,
            user_id=match["client_id"],
            studio_id=studio_id,
            notification_type=NotificationType.MATCH,
            priority=NotificationPriority.MEDIUM,
            title=f"Nuovo match normativo: {rule.name}",
            description=rule.description,
            reference_id=suggestion.id,
            reference_type="proactive_suggestion",
        )
        return True
    except Exception as exc:
        logger.warning(
            "matching_job_notification_error",
            rule_id=str(rule.id),
            client_id=match["client_id"],
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        return False
