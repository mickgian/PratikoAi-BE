"""DEV-308: StudioService — CRUD operations for Studio entity.

Manages Studio lifecycle: create, read, update, deactivate.
Enforces slug uniqueness and settings management.
"""

from datetime import UTC, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.studio import Studio


class StudioService:
    """Service for Studio CRUD with slug uniqueness validation."""

    async def create(
        self,
        db: AsyncSession,
        *,
        name: str,
        slug: str,
        max_clients: int = 100,
        settings: dict | None = None,
    ) -> Studio:
        """Create a new studio.

        Raises:
            ValueError: If slug is already in use.
        """
        await self._check_slug_available(db, slug)

        studio = Studio(
            name=name,
            slug=slug,
            max_clients=max_clients,
            settings=settings,
        )
        db.add(studio)
        await db.flush()

        logger.info("studio_created", studio_id=str(studio.id), slug=slug)
        return studio

    async def get_by_id(self, db: AsyncSession, *, studio_id: UUID) -> Studio | None:
        """Get studio by ID."""
        return await db.get(Studio, studio_id)

    async def get_by_slug(self, db: AsyncSession, *, slug: str) -> Studio | None:
        """Get studio by slug."""
        result = await db.execute(select(Studio).where(Studio.slug == slug))
        return result.scalar_one_or_none()

    async def update(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        name: str | None = None,
        slug: str | None = None,
        max_clients: int | None = None,
        settings: dict | None = None,
    ) -> Studio | None:
        """Update studio fields.

        Returns None if studio not found.
        Raises ValueError if new slug conflicts with another studio.
        """
        studio = await db.get(Studio, studio_id)
        if studio is None:
            return None

        if slug is not None and slug != studio.slug:
            await self._check_slug_available(db, slug, exclude_id=studio_id)
            studio.slug = slug

        if name is not None:
            studio.name = name
        if max_clients is not None:
            studio.max_clients = max_clients
        if settings is not None:
            studio.settings = settings

        studio.updated_at = datetime.now(UTC)
        await db.flush()

        logger.info("studio_updated", studio_id=str(studio_id))
        return studio

    async def deactivate(self, db: AsyncSession, *, studio_id: UUID) -> Studio | None:
        """Soft-deactivate a studio by setting updated_at.

        Returns None if studio not found.
        """
        studio = await db.get(Studio, studio_id)
        if studio is None:
            return None

        studio.updated_at = datetime.now(UTC)
        await db.flush()

        logger.info("studio_deactivated", studio_id=str(studio_id))
        return studio

    async def _check_slug_available(
        self,
        db: AsyncSession,
        slug: str,
        exclude_id: UUID | None = None,
    ) -> None:
        """Raise ValueError if slug is already taken."""
        query = select(Studio).where(Studio.slug == slug)
        if exclude_id is not None:
            query = query.where(Studio.id != exclude_id)
        result = await db.execute(query)
        if result.scalar_one_or_none() is not None:
            raise ValueError(f"Lo slug '{slug}' è già in uso da un altro studio.")


studio_service = StudioService()
