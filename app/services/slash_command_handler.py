"""Slash Command Handler (DEV-402, ADR-038).

Parses slash commands from chat input:
- /procedura [query] — Shows searchable procedure list (DEV-402)
- /consigli — Generates insight report (ADR-038)
"""

import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.procedura import ProceduraCategory
from app.services.procedura_service import procedura_service

# Pattern: /procedura [optional query]
SLASH_PROCEDURA_RE = re.compile(r"^/procedura(?:\s+(.+))?$", re.IGNORECASE)
# Pattern: /consigli (no arguments)
SLASH_CONSIGLI_RE = re.compile(r"^/consigli$", re.IGNORECASE)


class SlashCommandHandler:
    """Handles slash commands in chat input."""

    def parse(self, text: str) -> dict[str, Any] | None:
        """Parse chat input for slash commands.

        Returns:
            Dict with command info, or None if no slash command found.
        """
        text = text.strip()

        match = SLASH_PROCEDURA_RE.match(text)
        if match:
            query = (match.group(1) or "").strip()
            return {"command": "procedura", "query": query}

        if SLASH_CONSIGLI_RE.match(text):
            return {"command": "consigli"}

        return None

    async def handle_procedura(
        self,
        db: AsyncSession,
        *,
        query: str = "",
    ) -> dict[str, Any]:
        """Handle /procedura command — list or search procedures (read-only).

        No ProceduraProgress record is created (generic consultation mode).

        Args:
            db: Database session.
            query: Optional search query or procedure code.

        Returns:
            Dict with matching procedures or specific procedure details.
        """
        # Try exact code match first
        if query:
            proc = await procedura_service.get_by_code(db, code=query.upper())
            if proc is not None:
                logger.info("slash_procedura_exact_match", code=query)
                return {
                    "type": "detail",
                    "procedure": proc.to_dict(),
                    "mode": "read_only",
                }

        # Search by category if query matches
        category = self._match_category(query)
        if category is not None:
            procedures = await procedura_service.list_active(db, category=category)
        else:
            procedures = await procedura_service.list_active(db)

        # Filter by title if query provided and no category match
        if query and category is None:
            query_lower = query.lower()
            procedures = [
                p for p in procedures if query_lower in p.title.lower() or query_lower in (p.description or "").lower()
            ]

        logger.info(
            "slash_procedura_search",
            query=query,
            results_count=len(procedures),
        )

        return {
            "type": "list",
            "procedures": [p.to_dict() for p in procedures],
            "query": query,
            "mode": "read_only",
        }

    def _match_category(self, query: str) -> ProceduraCategory | None:
        """Try to match query to a ProceduraCategory."""
        if not query:
            return None
        query_lower = query.lower()
        for cat in ProceduraCategory:
            if cat.value == query_lower or query_lower in cat.value:
                return cat
        return None


slash_command_handler = SlashCommandHandler()
