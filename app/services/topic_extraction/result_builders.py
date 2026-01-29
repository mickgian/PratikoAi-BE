"""Result builders for routing decision operations."""

from typing import TYPE_CHECKING, Any

from app.schemas.router import RoutingCategory

if TYPE_CHECKING:
    from app.schemas.router import RouterDecision


def decision_to_dict(decision: "RouterDecision") -> dict[str, Any]:
    """Convert RouterDecision to a serializable dict for state storage.

    Args:
        decision: RouterDecision from LLMRouterService

    Returns:
        Dict representation with all fields serialized
    """
    return {
        "route": decision.route.value,  # Convert enum to string
        "confidence": decision.confidence,
        "reasoning": decision.reasoning,
        "entities": [
            {
                "text": entity.text,
                "type": entity.type,
                "confidence": entity.confidence,
            }
            for entity in decision.entities
        ],
        "requires_freshness": decision.requires_freshness,
        "suggested_sources": decision.suggested_sources,
        "needs_retrieval": decision.needs_retrieval,
        "is_followup": decision.is_followup,  # DEV-245: Follow-up detection
    }


def create_fallback_decision() -> dict[str, Any]:
    """Create a fallback routing decision for error cases.

    Falls back to TECHNICAL_RESEARCH which will trigger full RAG retrieval.

    Returns:
        Fallback routing decision dict
    """
    return {
        "route": RoutingCategory.TECHNICAL_RESEARCH.value,
        "confidence": 0.3,
        "reasoning": "Fallback: LLM router service unavailable, defaulting to technical research",
        "entities": [],
        "requires_freshness": False,
        "suggested_sources": [],
        "needs_retrieval": True,
        "is_followup": False,  # DEV-245: Default to not follow-up
    }
