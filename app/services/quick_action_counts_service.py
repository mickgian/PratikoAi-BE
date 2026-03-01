"""DEV-430: QuickActionCountsService — Live counts for Quick Action cards.

Returns counts for 6 card categories. Cached 5 min per studio.
Graceful degradation: returns 0 for categories on partial service failure.
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger

QUICK_ACTION_CACHE_TTL = 300  # 5 minutes
QUICK_ACTION_CACHE_PREFIX = "quick_actions:"


class QuickActionCountsService:
    """Service returning live counts for Quick Action cards."""

    async def get_counts(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
    ) -> dict[str, int]:
        """Return counts for 6 Quick Action categories.

        Returns 0 for categories not yet populated or on partial failure.
        """
        cached = await self._get_from_cache(studio_id)
        if cached is not None:
            return cached

        counts: dict[str, int] = {
            "modelli_formulari": await self._count_formulari(db),
            "scadenze_fiscali": await self._count_deadlines(db, studio_id),
            "aggiornamenti_urgenti": await self._count_urgent_notifications(db, studio_id),
            "normative_recenti": await self._count_recent_normative(db),
            "domande_pronte": await self._count_ready_questions(db, studio_id),
            "faq": await self._count_faq(db),
        }

        await self._set_cache(studio_id, counts)
        logger.info("quick_action_counts_aggregated", studio_id=str(studio_id))
        return counts

    async def _count_formulari(self, db: AsyncSession) -> int:
        """Count active formulari."""
        try:
            from app.models.formulario import Formulario

            result = await db.execute(select(func.count(Formulario.id)).where(Formulario.is_active.is_(True)))
            return result.scalar_one_or_none() or 0
        except Exception as e:
            logger.warning("quick_action_formulari_failed", error=str(e))
            return 0

    async def _count_deadlines(self, db: AsyncSession, studio_id: UUID) -> int:
        """Count upcoming active deadlines."""
        try:
            from datetime import date, timedelta

            from app.models.deadline import Deadline

            future = date.today() + timedelta(days=30)
            result = await db.execute(
                select(func.count(Deadline.id)).where(
                    Deadline.is_active.is_(True),
                    Deadline.due_date >= date.today(),
                    Deadline.due_date <= future,
                )
            )
            return result.scalar_one_or_none() or 0
        except Exception as e:
            logger.warning("quick_action_deadlines_failed", error=str(e))
            return 0

    async def _count_urgent_notifications(self, db: AsyncSession, studio_id: UUID) -> int:
        """Count unread urgent/high-priority notifications."""
        try:
            from app.models.notification import Notification, NotificationPriority

            result = await db.execute(
                select(func.count(Notification.id)).where(
                    Notification.studio_id == studio_id,
                    Notification.is_read.is_(False),
                    Notification.dismissed.is_(False),
                    Notification.priority.in_(
                        [
                            NotificationPriority.HIGH,
                            NotificationPriority.URGENT,
                        ]
                    ),
                )
            )
            return result.scalar_one_or_none() or 0
        except Exception as e:
            logger.warning("quick_action_urgent_failed", error=str(e))
            return 0

    async def _count_recent_normative(self, db: AsyncSession) -> int:
        """Count recent regulatory documents."""
        try:
            from app.models.regulatory_documents import RegulatoryDocument

            result = await db.execute(select(func.count(RegulatoryDocument.id)))
            return result.scalar_one_or_none() or 0
        except Exception as e:
            logger.warning("quick_action_normative_failed", error=str(e))
            return 0

    async def _count_ready_questions(self, db: AsyncSession, studio_id: UUID) -> int:
        """Count ready interactive questions/suggestions."""
        try:
            from app.models.proactive_suggestion import ProactiveSuggestion

            result = await db.execute(
                select(func.count(ProactiveSuggestion.id)).where(
                    ProactiveSuggestion.studio_id == studio_id,
                )
            )
            return result.scalar_one_or_none() or 0
        except Exception as e:
            logger.warning("quick_action_questions_failed", error=str(e))
            return 0

    async def _count_faq(self, db: AsyncSession) -> int:
        """Count active FAQ entries."""
        try:
            from app.models.faq import FAQEntry

            result = await db.execute(select(func.count(FAQEntry.id)).where(FAQEntry.is_active.is_(True)))
            return result.scalar_one_or_none() or 0
        except Exception as e:
            logger.warning("quick_action_faq_failed", error=str(e))
            return 0

    # ---------------------------------------------------------------
    # Cache helpers
    # ---------------------------------------------------------------

    async def _get_from_cache(self, studio_id: UUID) -> dict | None:
        try:
            from app.services.cache import cache_service

            r = await cache_service._get_redis()
            if not r:
                return None
            key = f"{QUICK_ACTION_CACHE_PREFIX}{studio_id}"
            data = await r.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning("quick_action_cache_get_failed", error=str(e))
        return None

    async def _set_cache(self, studio_id: UUID, data: dict) -> None:
        try:
            from app.services.cache import cache_service

            r = await cache_service._get_redis()
            if not r:
                return
            key = f"{QUICK_ACTION_CACHE_PREFIX}{studio_id}"
            await r.setex(key, QUICK_ACTION_CACHE_TTL, json.dumps(data))
        except Exception as e:
            logger.warning("quick_action_cache_set_failed", error=str(e))


quick_action_counts_service = QuickActionCountsService()
