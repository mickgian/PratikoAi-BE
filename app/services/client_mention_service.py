"""DEV-403: @client Mention System with Autocomplete.

Parses @mentions from chat, provides autocomplete, and injects
client context into RAGState. Supports action picker for:
generic question, client question, client card, start procedure.
"""

import re
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.client import Client

# Pattern: @ClientName or @"Client Name With Spaces"
MENTION_RE = re.compile(r'@"([^"]+)"|@(\S+)')


class ClientAction(StrEnum):
    """Actions available after selecting a client."""

    GENERIC_QUESTION = "generic_question"
    CLIENT_QUESTION = "client_question"
    CLIENT_CARD = "client_card"
    START_PROCEDURE = "start_procedure"


class ClientMentionService:
    """Service for @client mention parsing and autocomplete."""

    def extract_mentions(self, text: str) -> list[str]:
        """Extract @mentioned client names from text.

        Supports @Name and @"Full Name" syntax.
        """
        mentions: list[str] = []
        for match in MENTION_RE.finditer(text):
            # Group 1 for quoted, group 2 for unquoted
            name = match.group(1) or match.group(2)
            if name:
                mentions.append(name)
        return mentions

    async def autocomplete(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        prefix: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Autocomplete client names for @mention.

        Args:
            db: Database session.
            studio_id: Tenant isolation.
            prefix: Name prefix to search.
            limit: Max results (default 10).

        Returns:
            List of client dicts with id, nome, tipo_cliente.
        """
        if not prefix or len(prefix) < 2:
            return []

        result = await db.execute(
            select(Client)
            .where(
                and_(
                    Client.studio_id == studio_id,
                    Client.deleted_at.is_(None),
                    Client.nome.ilike(f"%{prefix}%"),
                )
            )
            .limit(limit)
        )
        clients = result.scalars().all()

        logger.info(
            "client_mention_autocomplete",
            studio_id=str(studio_id),
            prefix=prefix,
            results=len(clients),
        )

        return [
            {
                "id": c.id,
                "nome": c.nome,
                "tipo_cliente": c.tipo_cliente,
                "codice_fiscale": c.codice_fiscale,
            }
            for c in clients
        ]

    async def resolve_mention(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        client_name: str,
    ) -> Client | None:
        """Resolve a @mention to a Client record.

        Args:
            db: Database session.
            studio_id: Tenant isolation.
            client_name: Client name from @mention.

        Returns:
            Client or None if not found.
        """
        result = await db.execute(
            select(Client).where(
                and_(
                    Client.studio_id == studio_id,
                    Client.deleted_at.is_(None),
                    Client.nome.ilike(client_name),
                )
            )
        )
        client = result.scalars().first()

        if client:
            logger.info(
                "client_mention_resolved",
                studio_id=str(studio_id),
                client_id=client.id,
            )
        else:
            logger.info(
                "client_mention_not_found",
                studio_id=str(studio_id),
                client_name=client_name,
            )
        return client

    def get_available_actions(self, client_id: int | None = None) -> list[dict[str, str]]:
        """Get available actions for a mentioned client.

        Args:
            client_id: Optional client ID (None means no client context).

        Returns:
            List of action dicts with action, label, description.
        """
        actions = [
            {
                "action": ClientAction.GENERIC_QUESTION,
                "label": "Domanda generica",
                "description": "Fai una domanda generica sulla normativa",
            },
        ]

        if client_id is not None:
            actions.extend(
                [
                    {
                        "action": ClientAction.CLIENT_QUESTION,
                        "label": "Domanda sul cliente",
                        "description": "Fai una domanda relativa a questo cliente",
                    },
                    {
                        "action": ClientAction.CLIENT_CARD,
                        "label": "Scheda cliente",
                        "description": "Visualizza la scheda del cliente",
                    },
                    {
                        "action": ClientAction.START_PROCEDURE,
                        "label": "Avvia procedura",
                        "description": "Avvia una procedura per questo cliente",
                    },
                ]
            )

        return actions


client_mention_service = ClientMentionService()
