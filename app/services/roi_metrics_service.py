"""DEV-354: ROI Metrics Service.

Calculates ROI and usage statistics: time saved, communications sent,
regulations tracked.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger

# Estimated time per manual task (in minutes)
TIME_PER_CALCULATION = 15  # minutes saved per automated calculation
TIME_PER_COMMUNICATION = 30  # minutes saved per generated communication
TIME_PER_MATCHING = 45  # minutes saved per regulatory matching


class RoiMetricsService:
    """Service for calculating ROI and usage statistics."""

    async def get_studio_metrics(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
    ) -> dict[str, Any]:
        """Get aggregate metrics for a studio.

        Args:
            db: Database session.
            studio_id: Studio ID.

        Returns:
            Dict with metric counts.
        """
        from app.models.client import Client
        from app.models.communication import Communication

        # Count clients
        result = await db.execute(
            select(func.count(Client.id)).where(
                Client.studio_id == studio_id,
                Client.deleted_at.is_(None),
            )
        )
        total_clients = result.scalar_one_or_none() or 0

        # Count communications
        result = await db.execute(select(func.count(Communication.id)).where(Communication.studio_id == studio_id))
        communications_sent = result.scalar_one_or_none() or 0

        # Count calculations (if table exists)
        calculations = 0
        try:
            from app.models.calculation_history import CalculationHistory

            result = await db.execute(
                select(func.count(CalculationHistory.id)).where(CalculationHistory.studio_id == studio_id)
            )
            calculations = result.scalar_one_or_none() or 0
        except Exception:
            pass

        return {
            "total_clients": total_clients,
            "communications_sent": communications_sent,
            "calculations_performed": calculations,
        }

    async def estimate_time_saved(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
    ) -> dict[str, Any]:
        """Estimate time saved by using PratikoAI.

        Args:
            db: Database session.
            studio_id: Studio ID.

        Returns:
            Dict with hours_saved and breakdown.
        """
        metrics = await self.get_studio_metrics(db, studio_id=studio_id)

        calc_minutes = metrics["calculations_performed"] * TIME_PER_CALCULATION
        comm_minutes = metrics["communications_sent"] * TIME_PER_COMMUNICATION
        total_minutes = calc_minutes + comm_minutes

        return {
            "hours_saved": round(total_minutes / 60, 1),
            "breakdown": {
                "calculations_minutes": calc_minutes,
                "communications_minutes": comm_minutes,
            },
        }

    async def get_monthly_report(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        year: int,
        month: int,
    ) -> dict[str, Any]:
        """Get monthly metrics report.

        Args:
            db: Database session.
            studio_id: Studio ID.
            year: Year.
            month: Month (1-12).

        Returns:
            Dict with period and metrics.
        """
        metrics = await self.get_studio_metrics(db, studio_id=studio_id)
        time_saved = await self.estimate_time_saved(db, studio_id=studio_id)

        return {
            "period": f"{year}-{month:02d}",
            "studio_id": str(studio_id),
            "metrics": metrics,
            "time_saved": time_saved,
        }


roi_metrics_service = RoiMetricsService()
