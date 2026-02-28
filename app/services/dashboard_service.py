"""DEV-355 + DEV-358: Dashboard Data Aggregation with Redis Caching.

Aggregates data from multiple sources: client count, active procedures,
pending communications, recent matches, and ROI metrics.
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger

DASHBOARD_CACHE_TTL = 300  # 5 minutes
DASHBOARD_CACHE_PREFIX = "dashboard:"


class DashboardService:
    """Service aggregating dashboard data from multiple sources."""

    async def get_dashboard_data(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
    ) -> dict[str, Any]:
        """Aggregate all dashboard data for a studio.

        Returns dict with: clients, communications, procedures, matches, roi.
        """
        # Try cache first (DEV-358)
        cached = await self._get_from_cache(studio_id)
        if cached is not None:
            logger.info("dashboard_cache_hit", studio_id=str(studio_id))
            return cached

        data = {
            "clients": await self._get_client_stats(db, studio_id),
            "communications": await self._get_communication_stats(db, studio_id),
            "procedures": await self._get_procedure_stats(db, studio_id),
            "matches": await self._get_match_stats(db, studio_id),
            "roi": await self._get_roi_stats(db, studio_id),
        }

        # Cache the result (DEV-358)
        await self._set_cache(studio_id, data)

        logger.info("dashboard_data_aggregated", studio_id=str(studio_id))
        return data

    async def invalidate_cache(self, studio_id: UUID) -> None:
        """Invalidate dashboard cache for a studio."""
        try:
            from app.services.cache import cache_service

            r = await cache_service._get_redis()
            if r:
                key = f"{DASHBOARD_CACHE_PREFIX}{studio_id}"
                await r.delete(key)
                logger.info("dashboard_cache_invalidated", studio_id=str(studio_id))
        except Exception as e:
            logger.warning("dashboard_cache_invalidate_failed", error=str(e))

    # ---------------------------------------------------------------
    # Private aggregation helpers
    # ---------------------------------------------------------------

    async def _get_client_stats(self, db: AsyncSession, studio_id: UUID) -> dict[str, Any]:
        from app.models.client import Client

        result = await db.execute(
            select(func.count(Client.id)).where(
                Client.studio_id == studio_id,
                Client.deleted_at.is_(None),
            )
        )
        total = result.scalar_one_or_none() or 0
        return {"total": total}

    async def _get_communication_stats(self, db: AsyncSession, studio_id: UUID) -> dict[str, Any]:
        from app.models.communication import Communication, StatoComunicazione

        total_result = await db.execute(
            select(func.count(Communication.id)).where(Communication.studio_id == studio_id)
        )
        total = total_result.scalar_one_or_none() or 0

        pending_result = await db.execute(
            select(func.count(Communication.id)).where(
                Communication.studio_id == studio_id,
                Communication.status == StatoComunicazione.PENDING_REVIEW,
            )
        )
        pending = pending_result.scalar_one_or_none() or 0

        return {"total": total, "pending_review": pending}

    async def _get_procedure_stats(self, db: AsyncSession, studio_id: UUID) -> dict[str, Any]:
        from app.models.procedura_progress import ProceduraProgress

        total_result = await db.execute(
            select(func.count(ProceduraProgress.id)).where(
                ProceduraProgress.studio_id == studio_id,
            )
        )
        total = total_result.scalar_one_or_none() or 0

        active_result = await db.execute(
            select(func.count(ProceduraProgress.id)).where(
                ProceduraProgress.studio_id == studio_id,
                ProceduraProgress.completed_at.is_(None),
            )
        )
        active = active_result.scalar_one_or_none() or 0

        return {"total": total, "active": active}

    async def _get_match_stats(self, db: AsyncSession, studio_id: UUID) -> dict[str, Any]:
        from app.models.matching_rule import MatchingRule

        total_result = await db.execute(select(func.count(MatchingRule.id)).where(MatchingRule.is_active.is_(True)))
        total = total_result.scalar_one_or_none() or 0
        return {"active_rules": total}

    async def _get_roi_stats(self, db: AsyncSession, studio_id: UUID) -> dict[str, Any]:
        try:
            from app.services.roi_metrics_service import roi_metrics_service

            metrics = await roi_metrics_service.get_studio_metrics(db, studio_id=studio_id)
            time_saved = await roi_metrics_service.estimate_time_saved(db, studio_id=studio_id)
            return {**metrics, **time_saved}
        except Exception as e:
            logger.warning("dashboard_roi_failed", error=str(e))
            return {"hours_saved": 0, "breakdown": {}}

    # ---------------------------------------------------------------
    # Cache helpers (DEV-358)
    # ---------------------------------------------------------------

    async def _get_from_cache(self, studio_id: UUID) -> dict | None:
        try:
            from app.services.cache import cache_service

            r = await cache_service._get_redis()
            if not r:
                return None
            key = f"{DASHBOARD_CACHE_PREFIX}{studio_id}"
            data = await r.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning("dashboard_cache_get_failed", error=str(e))
        return None

    async def _set_cache(self, studio_id: UUID, data: dict) -> None:
        try:
            from app.services.cache import cache_service

            r = await cache_service._get_redis()
            if not r:
                return
            key = f"{DASHBOARD_CACHE_PREFIX}{studio_id}"
            await r.setex(key, DASHBOARD_CACHE_TTL, json.dumps(data))
        except Exception as e:
            logger.warning("dashboard_cache_set_failed", error=str(e))


dashboard_service = DashboardService()
