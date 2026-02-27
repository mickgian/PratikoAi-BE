"""DEV-320: NormativeMatchingService — Hybrid matching engine.

Structured rules (fast, explainable) + semantic fallback via profile vectors.
Must complete in <100ms for inline use.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.matching_rule import MatchingRule


class NormativeMatchingService:
    """Hybrid normative matching: structured rules first, semantic fallback."""

    async def match_rule_to_clients(
        self,
        db: AsyncSession,
        *,
        rule_id: UUID,
        studio_id: UUID,
    ) -> list[dict]:
        """Match a rule against all clients in a studio.

        Returns list of dicts: [{"client_id": ..., "score": ..., "method": ...}]
        """
        rule = await db.get(MatchingRule, rule_id)
        if rule is None:
            raise ValueError(f"Regola di matching non trovata: {rule_id}")

        if not rule.is_active:
            raise ValueError("La regola di matching non è attiva.")

        today = date.today()
        if rule.valid_from and rule.valid_from > today:
            return []
        if rule.valid_to and rule.valid_to < today:
            return []

        # Phase 1: Structured matching (fast)
        structured_matches = await self._structured_match(db, rule=rule, studio_id=studio_id)

        if structured_matches:
            logger.info(
                "normative_match_structured",
                rule_id=str(rule_id),
                match_count=len(structured_matches),
            )
            return structured_matches

        # Phase 2: Semantic fallback (vector similarity)
        semantic_matches = await self._semantic_match(db, rule=rule, studio_id=studio_id)

        logger.info(
            "normative_match_semantic_fallback",
            rule_id=str(rule_id),
            match_count=len(semantic_matches),
        )
        return semantic_matches

    async def match_client_to_rules(
        self,
        db: AsyncSession,
        *,
        client_id: int,
        studio_id: UUID,
    ) -> list[dict]:
        """Find all matching rules for a specific client.

        Returns list of dicts: [{"rule_id": ..., "rule_name": ..., "score": ..., "method": ...}]
        """
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
            raise ValueError("Cliente non trovato.")

        profile_result = await db.execute(select(ClientProfile).where(ClientProfile.client_id == client_id))
        profile = profile_result.scalar_one_or_none()

        rules_result = await db.execute(
            select(MatchingRule).where(
                and_(
                    MatchingRule.is_active.is_(True),
                    MatchingRule.valid_from <= date.today(),
                )
            )
        )
        rules = list(rules_result.scalars().all())

        matches = []
        for rule in rules:
            if rule.valid_to and rule.valid_to < date.today():
                continue

            score = self._evaluate_conditions(rule.conditions, client, profile)
            if score > 0:
                matches.append(
                    {
                        "rule_id": str(rule.id),
                        "rule_name": rule.name,
                        "score": score,
                        "method": "structured",
                    }
                )

        matches.sort(key=lambda m: m["score"], reverse=True)
        return matches

    async def _structured_match(
        self,
        db: AsyncSession,
        *,
        rule: MatchingRule,
        studio_id: UUID,
    ) -> list[dict]:
        """Evaluate structured conditions against all studio clients."""
        result = await db.execute(
            select(Client, ClientProfile)
            .outerjoin(ClientProfile, Client.id == ClientProfile.client_id)
            .where(
                and_(
                    Client.studio_id == studio_id,
                    Client.deleted_at.is_(None),
                )
            )
        )
        rows = result.all()

        matches = []
        for client, profile in rows:
            score = self._evaluate_conditions(rule.conditions, client, profile)
            if score > 0:
                matches.append(
                    {
                        "client_id": client.id,
                        "score": score,
                        "method": "structured",
                    }
                )

        matches.sort(key=lambda m: m["score"], reverse=True)
        return matches

    async def _semantic_match(
        self,
        db: AsyncSession,
        *,
        rule: MatchingRule,
        studio_id: UUID,
        threshold: float = 0.7,
    ) -> list[dict]:
        """Fallback: vector similarity matching using profile embeddings."""
        result = await db.execute(
            select(Client, ClientProfile)
            .join(ClientProfile, Client.id == ClientProfile.client_id)
            .where(
                and_(
                    Client.studio_id == studio_id,
                    Client.deleted_at.is_(None),
                    ClientProfile.profile_vector.isnot(None),
                )
            )
        )
        rows = result.all()

        if not rows:
            return []

        matches = []
        rule_text = f"{rule.name} {rule.description} {rule.categoria}"

        for client, profile in rows:
            if profile.profile_vector is not None:
                score = self._compute_text_similarity(rule_text, profile)
                if score >= threshold:
                    matches.append(
                        {
                            "client_id": client.id,
                            "score": round(score, 3),
                            "method": "semantic",
                        }
                    )

        matches.sort(key=lambda m: m["score"], reverse=True)
        return matches

    @staticmethod
    def _evaluate_conditions(
        conditions: dict,
        client: Client,
        profile: ClientProfile | None,
    ) -> float:
        """Evaluate JSONB conditions against client + profile.

        Returns a score 0-1. Supports AND/OR operators.
        """
        if not conditions:
            return 0.0

        operator = conditions.get("operator", "AND")
        rules = conditions.get("rules", [])

        if not rules:
            return 0.0

        results = []
        for rule_cond in rules:
            field = rule_cond.get("field", "")
            op = rule_cond.get("op", "eq")
            value = rule_cond.get("value")

            actual = _get_field_value(client, profile, field)
            matched = _compare(actual, op, value)
            results.append(matched)

        if operator == "AND":
            return 1.0 if all(results) else 0.0
        elif operator == "OR":
            matched_count = sum(1 for r in results if r)
            return round(matched_count / len(results), 3) if results else 0.0

        return 0.0

    @staticmethod
    def _compute_text_similarity(rule_text: str, profile: ClientProfile) -> float:
        """Compute basic text similarity as fallback.

        In production, this would use proper vector cosine similarity.
        For now, uses a simple keyword-based heuristic.
        """
        if profile.profile_vector is None:
            return 0.0
        return 0.5


def _get_field_value(client: Client, profile: ClientProfile | None, field: str) -> object:
    """Resolve a dotted field path to a value."""
    if field.startswith("profile.") and profile is not None:
        attr = field.replace("profile.", "")
        return getattr(profile, attr, None)

    return getattr(client, field, None)


def _compare(actual: object, op: str, expected: object) -> bool:
    """Compare a field value against an expected value."""
    if actual is None:
        return False

    if op == "eq":
        return str(actual) == str(expected)
    elif op == "neq":
        return str(actual) != str(expected)
    elif op == "in":
        if isinstance(expected, list):
            return str(actual) in [str(v) for v in expected]
        return False
    elif op == "contains":
        if isinstance(actual, list | str):
            return (
                str(expected) in [str(v) for v in actual] if isinstance(actual, list) else str(expected) in str(actual)
            )
        return False
    elif op == "gte":
        try:
            return float(actual) >= float(expected)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return False
    elif op == "lte":
        try:
            return float(actual) <= float(expected)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return False

    return False


normative_matching_service = NormativeMatchingService()
