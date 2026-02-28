"""DEV-352: Calculation History Service.

Stores and retrieves calculation history for audit and client records.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.calculation_history import CalculationHistory


class CalculationHistoryService:
    """Service for managing calculation history records."""

    async def record(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        calculation_type: str,
        input_data: dict[str, Any],
        result_data: dict[str, Any],
        client_id: int | None = None,
        performed_by: int | None = None,
        notes: str | None = None,
    ) -> CalculationHistory:
        """Record a calculation in history.

        Args:
            db: Database session.
            studio_id: Studio performing the calculation.
            calculation_type: Type (irpef, inps, iva, etc.).
            input_data: Input parameters.
            result_data: Calculation results.
            client_id: Optional client reference.
            performed_by: User who triggered the calculation.
            notes: Optional notes.

        Returns:
            Created CalculationHistory record.
        """
        record = CalculationHistory(
            studio_id=studio_id,
            calculation_type=calculation_type,
            input_data=input_data,
            result_data=result_data,
            client_id=client_id,
            performed_by=performed_by,
            notes=notes,
        )
        db.add(record)
        await db.flush()

        logger.info(
            "calculation_recorded",
            calculation_type=calculation_type,
            studio_id=str(studio_id),
            client_id=client_id,
        )
        return record

    async def list_by_client(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        client_id: int,
        calculation_type: str | None = None,
        limit: int = 50,
    ) -> list[CalculationHistory]:
        """List calculations for a client."""
        stmt = (
            select(CalculationHistory)
            .where(
                and_(
                    CalculationHistory.studio_id == studio_id,
                    CalculationHistory.client_id == client_id,
                )
            )
            .order_by(CalculationHistory.created_at.desc())
            .limit(limit)
        )
        if calculation_type:
            stmt = stmt.where(CalculationHistory.calculation_type == calculation_type)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_studio(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        calculation_type: str | None = None,
        limit: int = 100,
    ) -> list[CalculationHistory]:
        """List all calculations for a studio."""
        stmt = (
            select(CalculationHistory)
            .where(CalculationHistory.studio_id == studio_id)
            .order_by(CalculationHistory.created_at.desc())
            .limit(limit)
        )
        if calculation_type:
            stmt = stmt.where(CalculationHistory.calculation_type == calculation_type)

        result = await db.execute(stmt)
        return list(result.scalars().all())


calculation_history_service = CalculationHistoryService()
