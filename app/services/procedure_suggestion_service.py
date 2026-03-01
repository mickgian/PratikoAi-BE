"""DEV-429: ProcedureSuggestionService — Rule-based procedure suggestions per client.

Returns relevant procedures based on client profile (regime fiscale, ATECO, stato).
Cached per client for 1 hour. No LLM needed.
"""

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger

SUGGESTION_CACHE_TTL = 3600  # 1 hour
SUGGESTION_CACHE_PREFIX = "proc_suggestions:"


class ProcedureSuggestionService:
    """Rule-based procedure suggestions per client profile."""

    async def suggest_procedures(
        self,
        db: AsyncSession,
        *,
        client_id: int,
        studio_id: UUID,
    ) -> list[dict]:
        """Return relevant procedures for a client based on their profile.

        Returns list of {code, title, reason} dicts sorted by relevance.
        """
        cache_key = f"{SUGGESTION_CACHE_PREFIX}{studio_id}:{client_id}"
        cached = await self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        profile = await self._get_client_profile(db, client_id=client_id)
        client = await self._get_client(db, client_id=client_id, studio_id=studio_id)
        if client is None:
            return []

        procedures = await self._get_active_procedures(db)
        suggestions: list[dict] = []

        suggestions.extend(self._match_by_status(client, procedures))
        if profile:
            suggestions.extend(self._match_by_regime(profile, procedures))
            suggestions.extend(self._match_by_ateco(profile, procedures))

        # Deduplicate by code, keeping first match (highest priority)
        seen: set[str] = set()
        unique: list[dict] = []
        for s in suggestions:
            if s["code"] not in seen:
                seen.add(s["code"])
                unique.append(s)

        await self._set_cache(cache_key, unique)
        logger.info(
            "procedure_suggestions_generated",
            client_id=client_id,
            count=len(unique),
        )
        return unique

    def _match_by_status(self, client: object, procedures: list) -> list[dict]:
        """Suggest procedures based on client lifecycle state."""
        from app.models.client import StatoCliente

        suggestions = []
        stato = getattr(client, "stato_cliente", None)

        if stato == StatoCliente.PROSPECT:
            for p in procedures:
                if "apertura" in p.code.lower() or "apertura" in p.title.lower():
                    suggestions.append(
                        {
                            "code": p.code,
                            "title": p.title,
                            "reason": "Cliente prospect — procedura di apertura consigliata",
                        }
                    )
        elif stato == StatoCliente.CESSATO:
            for p in procedures:
                if "chiusura" in p.code.lower() or "cessazione" in p.title.lower():
                    suggestions.append(
                        {
                            "code": p.code,
                            "title": p.title,
                            "reason": "Cliente cessato — procedura di chiusura applicabile",
                        }
                    )

        return suggestions

    def _match_by_regime(self, profile: object, procedures: list) -> list[dict]:
        """Suggest procedures based on fiscal regime."""
        from app.models.client_profile import RegimeFiscale

        suggestions = []
        regime = getattr(profile, "regime_fiscale", None)

        if regime == RegimeFiscale.FORFETTARIO:
            for p in procedures:
                if "trasformazione" in p.code.lower() or "regime" in p.title.lower():
                    suggestions.append(
                        {
                            "code": p.code,
                            "title": p.title,
                            "reason": "Regime forfettario — possibile trasformazione regime",
                        }
                    )
        elif regime == RegimeFiscale.SEMPLIFICATO:
            for p in procedures:
                if "ordinario" in p.code.lower() or "passaggio" in p.title.lower():
                    suggestions.append(
                        {
                            "code": p.code,
                            "title": p.title,
                            "reason": "Regime semplificato — valutare passaggio a ordinario",
                        }
                    )

        return suggestions

    def _match_by_ateco(self, profile: object, procedures: list) -> list[dict]:
        """Suggest procedures based on ATECO code."""
        suggestions = []
        ateco = getattr(profile, "codice_ateco_principale", None)
        if not ateco:
            return suggestions

        # Construction sector (41-43)
        if ateco.startswith(("41.", "42.", "43.")):
            for p in procedures:
                if "cantiere" in p.title.lower() or "sicurezza" in p.title.lower():
                    suggestions.append(
                        {
                            "code": p.code,
                            "title": p.title,
                            "reason": f"Settore edile (ATECO {ateco}) — procedura sicurezza",
                        }
                    )

        return suggestions

    async def _get_client(self, db: AsyncSession, *, client_id: int, studio_id: UUID) -> object | None:
        from app.models.client import Client

        result = await db.execute(
            select(Client).where(
                Client.id == client_id,
                Client.studio_id == studio_id,
                Client.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _get_client_profile(self, db: AsyncSession, *, client_id: int) -> object | None:
        from app.models.client_profile import ClientProfile

        result = await db.execute(select(ClientProfile).where(ClientProfile.client_id == client_id))
        return result.scalar_one_or_none()

    async def _get_active_procedures(self, db: AsyncSession) -> list:
        from app.models.procedura import Procedura

        result = await db.execute(select(Procedura).where(Procedura.is_active.is_(True)))
        return list(result.scalars().all())

    # ---------------------------------------------------------------
    # Cache helpers
    # ---------------------------------------------------------------

    async def _get_from_cache(self, key: str) -> list | None:
        try:
            from app.services.cache import cache_service

            r = await cache_service._get_redis()
            if not r:
                return None
            data = await r.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    async def _set_cache(self, key: str, data: list) -> None:
        try:
            from app.services.cache import cache_service

            r = await cache_service._get_redis()
            if not r:
                return
            await r.setex(key, SUGGESTION_CACHE_TTL, json.dumps(data))
        except Exception:
            pass


procedure_suggestion_service = ProcedureSuggestionService()
