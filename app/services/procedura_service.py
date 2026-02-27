"""DEV-340: ProceduraService — Procedure lifecycle with progress tracking.

Manages procedures (list, get by code) and user progress through
multi-step interactive procedures (start, advance, complete).
"""

from datetime import UTC, datetime, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.procedura import Procedura, ProceduraCategory
from app.models.procedura_progress import ProceduraProgress


class ProceduraService:
    """Service for procedure management and progress tracking."""

    # ---------------------------------------------------------------
    # Procedure retrieval
    # ---------------------------------------------------------------

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Procedura | None:
        """Get procedure by unique code."""
        result = await db.execute(select(Procedura).where(Procedura.code == code))
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, *, procedura_id: UUID) -> Procedura | None:
        """Get procedure by ID."""
        return await db.get(Procedura, procedura_id)

    async def list_active(
        self,
        db: AsyncSession,
        *,
        category: ProceduraCategory | None = None,
    ) -> list[Procedura]:
        """List active procedures, optionally filtered by category."""
        query = select(Procedura).where(Procedura.is_active.is_(True))
        if category is not None:
            query = query.where(Procedura.category == category)
        query = query.order_by(Procedura.title)

        result = await db.execute(query)
        return list(result.scalars().all())

    # ---------------------------------------------------------------
    # Progress tracking
    # ---------------------------------------------------------------

    async def start_progress(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
        procedura_id: UUID,
        client_id: int | None = None,
    ) -> ProceduraProgress:
        """Start tracking progress for a user/procedure pair.

        Raises:
            ValueError: If user already has active progress for this procedure.
        """
        existing = await self._get_active_progress(db, user_id=user_id, studio_id=studio_id, procedura_id=procedura_id)
        if existing is not None:
            raise ValueError(f"Il progresso per la procedura è già esistente per l'utente {user_id}.")

        progress = ProceduraProgress(
            user_id=user_id,
            studio_id=studio_id,
            procedura_id=procedura_id,
            client_id=client_id,
            current_step=0,
            completed_steps=[],
        )
        db.add(progress)
        await db.flush()

        logger.info(
            "procedura_progress_started",
            user_id=user_id,
            procedura_id=str(procedura_id),
        )
        return progress

    async def advance_step(self, db: AsyncSession, *, progress_id: UUID) -> ProceduraProgress | None:
        """Advance to next step, completing procedure if at the last step.

        Returns None if progress not found.
        """
        result = await db.execute(select(ProceduraProgress).where(ProceduraProgress.id == progress_id))
        progress = result.scalar_one_or_none()
        if progress is None:
            return None

        # Get the procedure to know total steps
        proc_result = await db.execute(select(Procedura).where(Procedura.id == progress.procedura_id))
        procedura = proc_result.scalar_one_or_none()
        if procedura is None:
            return None

        total_steps = len(procedura.steps)
        current = progress.current_step

        # Mark current step as completed
        completed = list(progress.completed_steps)
        if current not in completed:
            completed.append(current)
        progress.completed_steps = completed

        # Check if this is the last step
        if current >= total_steps - 1:
            progress.completed_at = datetime.now(UTC)
            logger.info(
                "procedura_completed",
                progress_id=str(progress_id),
            )
        else:
            progress.current_step = current + 1

        await db.flush()

        logger.info(
            "procedura_step_advanced",
            progress_id=str(progress_id),
            step=progress.current_step,
        )
        return progress

    async def get_progress(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
        procedura_id: UUID,
    ) -> ProceduraProgress | None:
        """Get user's progress for a specific procedure."""
        return await self._get_active_progress(db, user_id=user_id, studio_id=studio_id, procedura_id=procedura_id)

    async def list_user_progress(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
    ) -> list[ProceduraProgress]:
        """List all progress records for a user in a studio."""
        result = await db.execute(
            select(ProceduraProgress).where(
                and_(
                    ProceduraProgress.user_id == user_id,
                    ProceduraProgress.studio_id == studio_id,
                )
            )
        )
        return list(result.scalars().all())

    # ---------------------------------------------------------------
    # DEV-343: Checklist item tracking
    # ---------------------------------------------------------------

    async def update_checklist_item(
        self,
        db: AsyncSession,
        *,
        progress_id: UUID,
        step_index: int,
        item_index: int,
        completed: bool,
    ) -> ProceduraProgress | None:
        """Update completion status of a checklist item within a step.

        Raises ValueError if step_index or item_index is out of bounds.
        """
        result = await db.execute(select(ProceduraProgress).where(ProceduraProgress.id == progress_id))
        progress = result.scalar_one_or_none()
        if progress is None:
            return None

        proc = await db.get(Procedura, progress.procedura_id)
        if proc is None:
            return None

        if step_index < 0 or step_index >= len(proc.steps):
            raise ValueError(f"Indice step non valido: {step_index}")

        step = proc.steps[step_index]
        checklist = step.get("checklist", [])
        if item_index < 0 or item_index >= len(checklist):
            raise ValueError(f"Indice item checklist non valido: {item_index}")

        # Track checklist items in dedicated JSONB field: {"step_idx": {"item_idx": bool}}
        state = dict(progress.checklist_state) if progress.checklist_state else {}
        step_key = str(step_index)
        if step_key not in state:
            state[step_key] = {}
        state[step_key][str(item_index)] = completed
        progress.checklist_state = state

        await db.flush()

        logger.info(
            "checklist_item_updated",
            progress_id=str(progress_id),
            step_index=step_index,
            item_index=item_index,
            completed=completed,
        )
        return progress

    # ---------------------------------------------------------------
    # DEV-344: Notes and document checklist
    # ---------------------------------------------------------------

    async def update_notes(
        self,
        db: AsyncSession,
        *,
        progress_id: UUID,
        notes: str | None,
    ) -> ProceduraProgress | None:
        """Update notes for a progress record."""
        result = await db.execute(select(ProceduraProgress).where(ProceduraProgress.id == progress_id))
        progress = result.scalar_one_or_none()
        if progress is None:
            return None

        progress.notes = notes
        await db.flush()

        logger.info("procedura_notes_updated", progress_id=str(progress_id))
        return progress

    async def update_document_status(
        self,
        db: AsyncSession,
        *,
        progress_id: UUID,
        document_name: str,
        verified: bool,
    ) -> ProceduraProgress | None:
        """Update document verification status (checkbox-based, no file upload).

        ADR-036: Only track verified/not-verified status per document.
        Raises ValueError if document_name is not in the procedure's document list.
        """
        result = await db.execute(select(ProceduraProgress).where(ProceduraProgress.id == progress_id))
        progress = result.scalar_one_or_none()
        if progress is None:
            return None

        proc = await db.get(Procedura, progress.procedura_id)
        if proc is None:
            return None

        # Collect all document names from all steps
        all_docs: set[str] = set()
        for step in proc.steps:
            docs = step.get("documents", [])
            for doc in docs:
                if isinstance(doc, str):
                    all_docs.add(doc)
                elif isinstance(doc, dict):
                    all_docs.add(doc.get("name", ""))

        if document_name not in all_docs:
            raise ValueError(f"Il documento '{document_name}' non è presente nella procedura.")

        # Store in dedicated JSONB field: {"doc_name": bool}
        doc_status = dict(progress.document_status) if progress.document_status else {}
        doc_status[document_name] = verified
        progress.document_status = doc_status
        await db.flush()

        logger.info(
            "procedura_document_status_updated",
            progress_id=str(progress_id),
            document=document_name,
            verified=verified,
        )
        return progress

    # ---------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------

    async def _get_active_progress(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
        procedura_id: UUID,
    ) -> ProceduraProgress | None:
        """Get active (non-completed) progress for a user/procedure."""
        result = await db.execute(
            select(ProceduraProgress).where(
                and_(
                    ProceduraProgress.user_id == user_id,
                    ProceduraProgress.studio_id == studio_id,
                    ProceduraProgress.procedura_id == procedura_id,
                    ProceduraProgress.completed_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()


procedura_service = ProceduraService()
