"""DEV-373: DPA Acceptance Workflow — GDPR Data Processing Agreement service.

Manages DPA versions and studio acceptance. Users must accept DPA before adding clients.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.dpa import DPA, DPAAcceptance, DPAStatus


class DPAService:
    """Service for DPA management and acceptance workflow."""

    async def get_active_dpa(self, db: AsyncSession) -> DPA | None:
        """Get the current active DPA version."""
        result = await db.execute(
            select(DPA).where(DPA.status == DPAStatus.ACTIVE).order_by(DPA.effective_from.desc())
        )
        return result.scalars().first()

    async def get_by_id(self, db: AsyncSession, *, dpa_id: UUID) -> DPA | None:
        """Get a DPA by ID."""
        return await db.get(DPA, dpa_id)

    async def accept(
        self,
        db: AsyncSession,
        *,
        dpa_id: UUID,
        studio_id: UUID,
        accepted_by: int,
        ip_address: str,
        user_agent: str | None = None,
    ) -> DPAAcceptance:
        """Record a studio's acceptance of a DPA version.

        Raises ValueError if already accepted.
        """
        existing = await db.execute(
            select(DPAAcceptance).where(
                and_(
                    DPAAcceptance.dpa_id == dpa_id,
                    DPAAcceptance.studio_id == studio_id,
                )
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError("Il DPA è già stato accettato dallo studio.")

        dpa = await db.get(DPA, dpa_id)
        if dpa is None:
            raise ValueError("DPA non trovato.")
        if dpa.status != DPAStatus.ACTIVE:
            raise ValueError("Il DPA non è in stato attivo.")

        acceptance = DPAAcceptance(
            dpa_id=dpa_id,
            studio_id=studio_id,
            accepted_by=accepted_by,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(acceptance)
        await db.flush()

        logger.info(
            "dpa_accepted",
            dpa_id=str(dpa_id),
            studio_id=str(studio_id),
            accepted_by=accepted_by,
        )
        return acceptance

    async def check_accepted(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
    ) -> bool:
        """Check if studio has accepted the current active DPA."""
        active_dpa = await self.get_active_dpa(db)
        if active_dpa is None:
            return False

        result = await db.execute(
            select(DPAAcceptance).where(
                and_(
                    DPAAcceptance.dpa_id == active_dpa.id,
                    DPAAcceptance.studio_id == studio_id,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def revoke_acceptance(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        dpa_id: UUID,
    ) -> bool:
        """Revoke a studio's DPA acceptance. Returns True if revoked."""
        result = await db.execute(
            select(DPAAcceptance).where(
                and_(
                    DPAAcceptance.dpa_id == dpa_id,
                    DPAAcceptance.studio_id == studio_id,
                )
            )
        )
        acceptance = result.scalar_one_or_none()
        if acceptance is None:
            return False

        await db.delete(acceptance)
        await db.flush()

        logger.info(
            "dpa_acceptance_revoked",
            dpa_id=str(dpa_id),
            studio_id=str(studio_id),
        )
        return True

    async def list_acceptances(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
    ) -> list[DPAAcceptance]:
        """List all DPA acceptances for a studio."""
        result = await db.execute(select(DPAAcceptance).where(DPAAcceptance.studio_id == studio_id))
        return list(result.scalars().all())


dpa_service = DPAService()
