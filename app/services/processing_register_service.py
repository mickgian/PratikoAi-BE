"""DEV-376: Processing Register Service — GDPR register of processing activities.

Tracks what data is processed, why, and the legal basis.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.processing_register import ProcessingRegister


class ProcessingRegisterService:
    """Service for GDPR processing register management."""

    async def create(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        activity_name: str,
        purpose: str,
        legal_basis: str,
        data_categories: list[str],
        data_subjects: str,
        retention_period: str,
        recipients: list[str] | None = None,
        third_country_transfers: bool = False,
        notes: str | None = None,
    ) -> ProcessingRegister:
        """Create a new processing activity entry."""
        entry = ProcessingRegister(
            studio_id=studio_id,
            activity_name=activity_name,
            purpose=purpose,
            legal_basis=legal_basis,
            data_categories=data_categories,
            data_subjects=data_subjects,
            retention_period=retention_period,
            recipients=recipients,
            third_country_transfers=third_country_transfers,
            notes=notes,
        )
        db.add(entry)
        await db.flush()

        logger.info(
            "processing_register_created",
            entry_id=str(entry.id),
            studio_id=str(studio_id),
            activity_name=activity_name,
        )
        return entry

    async def get_by_id(self, db: AsyncSession, *, entry_id: UUID, studio_id: UUID) -> ProcessingRegister | None:
        """Get processing register entry by ID within studio."""
        result = await db.execute(
            select(ProcessingRegister).where(
                and_(
                    ProcessingRegister.id == entry_id,
                    ProcessingRegister.studio_id == studio_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_by_studio(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
    ) -> list[ProcessingRegister]:
        """List all processing activities for a studio."""
        result = await db.execute(
            select(ProcessingRegister)
            .where(ProcessingRegister.studio_id == studio_id)
            .order_by(ProcessingRegister.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(
        self,
        db: AsyncSession,
        *,
        entry_id: UUID,
        studio_id: UUID,
        **fields: object,
    ) -> ProcessingRegister | None:
        """Update a processing register entry."""
        entry = await self.get_by_id(db, entry_id=entry_id, studio_id=studio_id)
        if entry is None:
            return None

        for key, value in fields.items():
            if hasattr(entry, key) and value is not None:
                setattr(entry, key, value)

        entry.updated_at = datetime.now(UTC)
        await db.flush()

        logger.info("processing_register_updated", entry_id=str(entry_id))
        return entry

    async def delete(
        self,
        db: AsyncSession,
        *,
        entry_id: UUID,
        studio_id: UUID,
    ) -> bool:
        """Delete a processing register entry. Returns True if deleted."""
        entry = await self.get_by_id(db, entry_id=entry_id, studio_id=studio_id)
        if entry is None:
            return False

        await db.delete(entry)
        await db.flush()

        logger.info("processing_register_deleted", entry_id=str(entry_id))
        return True


processing_register_service = ProcessingRegisterService()
