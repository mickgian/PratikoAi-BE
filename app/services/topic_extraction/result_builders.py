"""Result builders for routing decision operations."""

from typing import TYPE_CHECKING, Any

from app.schemas.router import RoutingCategory

if TYPE_CHECKING:
    from app.schemas.router import RouterDecision
    from app.services.hf_intent_classifier import IntentResult


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


def hf_result_to_decision_dict(hf_result: "IntentResult") -> dict[str, Any]:
    """Convert HuggingFace IntentResult to a routing decision dict.

    DEV-251: Enables using HF zero-shot classifier results in the routing pipeline.

    Args:
        hf_result: IntentResult from HFIntentClassifier.classify()

    Returns:
        Routing decision dict compatible with LLM router format
    """
    # Map HF intent to RoutingCategory (they use the same string values)
    route = hf_result.intent

    # Determine if retrieval is needed based on route
    retrieval_routes = {"technical_research", "theoretical_definition", "golden_set"}
    needs_retrieval = route in retrieval_routes

    return {
        "route": route,
        "confidence": hf_result.confidence,
        "reasoning": f"HuggingFace zero-shot classification (confidence: {hf_result.confidence:.2f})",
        "entities": [],  # HF classifier doesn't extract entities
        "requires_freshness": False,
        "suggested_sources": [],
        "needs_retrieval": needs_retrieval,
        "is_followup": False,  # HF can't detect follow-ups, GPT fallback handles this
    }
