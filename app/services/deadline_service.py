"""DEV-381: DeadlineService — CRUD with studio isolation and status management.

Manages deadlines and client-deadline associations.
"""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.deadline import ClientDeadline, Deadline, DeadlineSource, DeadlineType


class DeadlineService:
    """Service for deadline CRUD with studio-level isolation."""

    async def create(
        self,
        db: AsyncSession,
        *,
        title: str,
        deadline_type: DeadlineType,
        source: DeadlineSource,
        due_date: date,
        description: str | None = None,
        recurrence_rule: str | None = None,
    ) -> Deadline:
        """Create a new deadline definition."""
        deadline = Deadline(
            title=title,
            description=description,
            deadline_type=deadline_type,
            source=source,
            due_date=due_date,
            recurrence_rule=recurrence_rule,
        )
        db.add(deadline)
        await db.flush()

        logger.info("deadline_created", deadline_id=str(deadline.id), title=title)
        return deadline

    async def get_by_id(self, db: AsyncSession, *, deadline_id: UUID) -> Deadline | None:
        """Get deadline by ID."""
        return await db.get(Deadline, deadline_id)

    async def list_active(
        self,
        db: AsyncSession,
        *,
        deadline_type: DeadlineType | None = None,
        source: DeadlineSource | None = None,
    ) -> list[Deadline]:
        """List active deadlines with optional filters."""
        query = select(Deadline).where(Deadline.is_active.is_(True))
        if deadline_type is not None:
            query = query.where(Deadline.deadline_type == deadline_type)
        if source is not None:
            query = query.where(Deadline.source == source)
        query = query.order_by(Deadline.due_date)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def list_upcoming(
        self,
        db: AsyncSession,
        *,
        days_ahead: int = 30,
    ) -> list[Deadline]:
        """List deadlines due within the next N days."""
        today = date.today()
        future = date.fromordinal(today.toordinal() + days_ahead)

        result = await db.execute(
            select(Deadline)
            .where(
                and_(
                    Deadline.is_active.is_(True),
                    Deadline.due_date >= today,
                    Deadline.due_date <= future,
                )
            )
            .order_by(Deadline.due_date)
        )
        return list(result.scalars().all())

    async def update(
        self,
        db: AsyncSession,
        *,
        deadline_id: UUID,
        **fields: object,
    ) -> Deadline | None:
        """Update deadline fields. Returns None if not found."""
        deadline = await db.get(Deadline, deadline_id)
        if deadline is None:
            return None

        for key, value in fields.items():
            if hasattr(deadline, key) and value is not None:
                setattr(deadline, key, value)

        await db.flush()
        logger.info("deadline_updated", deadline_id=str(deadline_id))
        return deadline

    async def deactivate(self, db: AsyncSession, *, deadline_id: UUID) -> Deadline | None:
        """Deactivate a deadline."""
        deadline = await db.get(Deadline, deadline_id)
        if deadline is None:
            return None

        deadline.is_active = False
        await db.flush()
        logger.info("deadline_deactivated", deadline_id=str(deadline_id))
        return deadline

    # ---------------------------------------------------------------
    # Client-Deadline associations
    # ---------------------------------------------------------------

    async def assign_to_client(
        self,
        db: AsyncSession,
        *,
        client_id: int,
        deadline_id: UUID,
        studio_id: UUID,
        notes: str | None = None,
    ) -> ClientDeadline:
        """Assign a deadline to a client.

        Raises ValueError if already assigned.
        """
        existing = await db.execute(
            select(ClientDeadline).where(
                and_(
                    ClientDeadline.client_id == client_id,
                    ClientDeadline.deadline_id == deadline_id,
                )
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError("La scadenza è già assegnata al cliente.")

        cd = ClientDeadline(
            client_id=client_id,
            deadline_id=deadline_id,
            studio_id=studio_id,
            notes=notes,
        )
        db.add(cd)
        await db.flush()

        logger.info(
            "deadline_assigned",
            client_id=client_id,
            deadline_id=str(deadline_id),
        )
        return cd

    async def mark_completed(
        self,
        db: AsyncSession,
        *,
        client_deadline_id: UUID,
    ) -> ClientDeadline | None:
        """Mark a client-deadline as completed."""
        cd = await db.get(ClientDeadline, client_deadline_id)
        if cd is None:
            return None

        cd.is_completed = True
        cd.completed_at = datetime.now(UTC)
        await db.flush()

        logger.info("deadline_completed", client_deadline_id=str(client_deadline_id))
        return cd

    async def list_by_studio(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        completed: bool | None = None,
    ) -> list[ClientDeadline]:
        """List client-deadline associations for a studio."""
        query = select(ClientDeadline).where(ClientDeadline.studio_id == studio_id)
        if completed is not None:
            query = query.where(ClientDeadline.is_completed == completed)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def list_by_client(
        self,
        db: AsyncSession,
        *,
        client_id: int,
        studio_id: UUID,
    ) -> list[ClientDeadline]:
        """List deadlines for a specific client."""
        result = await db.execute(
            select(ClientDeadline).where(
                and_(
                    ClientDeadline.client_id == client_id,
                    ClientDeadline.studio_id == studio_id,
                )
            )
        )
        return list(result.scalars().all())


deadline_service = DeadlineService()
