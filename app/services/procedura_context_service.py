"""DEV-345: Procedura Context in Chat — Injects procedure and client context into RAGState.

When user has active procedura, adds procedure context.
When @NomeCliente mentioned, injects client profile.
"""

import re
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.procedura import Procedura
from app.models.procedura_progress import ProceduraProgress


class ProceduraContextService:
    """Service for building procedura and client context for chat."""

    async def build_procedura_context(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        studio_id: UUID,
    ) -> dict | None:
        """Build context dict for active procedura.

        Returns None if no active procedura.
        Returns dict with procedure info, current step, and progress.
        """
        result = await db.execute(
            select(ProceduraProgress)
            .where(
                and_(
                    ProceduraProgress.user_id == user_id,
                    ProceduraProgress.studio_id == studio_id,
                    ProceduraProgress.completed_at.is_(None),
                )
            )
            .order_by(ProceduraProgress.started_at.desc())
        )
        progress = result.scalars().first()
        if progress is None:
            return None

        proc = await db.get(Procedura, progress.procedura_id)
        if proc is None:
            return None

        current_step_info = None
        if proc.steps and 0 <= progress.current_step < len(proc.steps):
            current_step_info = proc.steps[progress.current_step]

        context = {
            "procedura_code": proc.code,
            "procedura_title": proc.title,
            "procedura_category": proc.category,
            "current_step": progress.current_step,
            "total_steps": len(proc.steps),
            "current_step_info": current_step_info,
            "completed_steps": progress.completed_steps,
            "notes": progress.notes,
        }

        # Include client info if linked
        if progress.client_id is not None:
            client_context = await self._build_client_context(db, client_id=progress.client_id, studio_id=studio_id)
            if client_context:
                context["client"] = client_context

        logger.info(
            "procedura_context_built",
            user_id=user_id,
            procedura_code=proc.code,
            step=progress.current_step,
        )
        return context

    async def resolve_client_mention(
        self,
        db: AsyncSession,
        *,
        message: str,
        studio_id: UUID,
    ) -> dict | None:
        """Extract @NomeCliente mention and return client context.

        Returns None if no mention found or client not found.
        """
        match = re.search(r"@(\w+(?:\s+\w+)?)", message)
        if not match:
            return None

        name_query = match.group(1)

        result = await db.execute(
            select(Client).where(
                and_(
                    Client.studio_id == studio_id,
                    Client.deleted_at.is_(None),
                )
            )
        )
        clients = result.scalars().all()

        for client in clients:
            client_name = str(client.nome).lower() if client.nome else ""
            if name_query.lower() in client_name:
                context = await self._build_client_context(db, client_id=client.id, studio_id=studio_id)
                if context:
                    logger.info(
                        "client_mention_resolved",
                        name_query=name_query,
                        client_id=client.id,
                    )
                    return context

        logger.warning(
            "client_mention_not_found",
            name_query=name_query,
            studio_id=str(studio_id),
        )
        return None

    async def _build_client_context(
        self,
        db: AsyncSession,
        *,
        client_id: int,
        studio_id: UUID,
    ) -> dict | None:
        """Build context dict for a specific client."""
        result = await db.execute(
            select(Client).where(
                and_(
                    Client.id == client_id,
                    Client.studio_id == studio_id,
                    Client.deleted_at.is_(None),
                )
            )
        )
        client = result.scalar_one_or_none()
        if client is None:
            return None

        context: dict = {
            "client_id": client.id,
            "nome": client.nome,
            "tipo_cliente": (
                client.tipo_cliente.value if hasattr(client.tipo_cliente, "value") else str(client.tipo_cliente)
            ),
            "comune": client.comune,
            "provincia": client.provincia,
        }

        profile_result = await db.execute(select(ClientProfile).where(ClientProfile.client_id == client_id))
        profile = profile_result.scalar_one_or_none()
        if profile:
            context["codice_ateco"] = profile.codice_ateco_principale
            context["regime_fiscale"] = (
                profile.regime_fiscale.value
                if hasattr(profile.regime_fiscale, "value")
                else str(profile.regime_fiscale)
            )
            context["n_dipendenti"] = profile.n_dipendenti

        return context


procedura_context_service = ProceduraContextService()
