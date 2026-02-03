"""Result builders for routing decision operations."""

import re
from typing import TYPE_CHECKING, Any

from app.schemas.router import RoutingCategory

if TYPE_CHECKING:
    from app.schemas.router import RouterDecision
    from app.services.hf_intent_classifier import IntentResult


def _detect_followup_from_query(query: str) -> bool:
    """DEV-251 Part 3.1: Detect follow-up patterns in query text.

    Identifies follow-up questions that should receive concise responses
    without repeating previously provided information.

    Args:
        query: The user's query text

    Returns:
        True if the query appears to be a follow-up question
    """
    if not query:
        return False

    query_lower = query.lower().strip()

    # Pattern 1: Starts with continuation conjunctions (Italian)
    followup_starters = (
        "e ",
        "e l'",
        "e il ",
        "e la ",
        "e i ",
        "e le ",
        "e gli ",
        "ma ",
        "però ",
        "anche ",
        "invece ",
        "e per ",
    )
    if any(query_lower.startswith(s) for s in followup_starters):
        return True

    # Pattern 2: Very short question (<6 words) assuming context
    words = query.split()
    if len(words) < 6 and query.endswith("?"):
        return True

    # Pattern 3: Anaphoric references (Italian)
    # Note: We check for word boundaries to avoid false positives like "termine per"
    # Patterns that should match with word boundaries
    anaphora_patterns = (
        r"\bquesto\b",  # "questo vale anche..." but not "contesto"
        r"\bquello\b",  # "quello che hai detto..."
        r"\blo stesso\b",  # "lo stesso per..."
        r"\banche per\b",  # "anche per i dipendenti?"
        r"\briguardo a questo\b",
        r"\bin questo caso\b",
    )
    return any(re.search(p, query_lower) for p in anaphora_patterns)


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


def hf_result_to_decision_dict(
    hf_result: "IntentResult",
    query: str = "",
) -> dict[str, Any]:
    """Convert HuggingFace IntentResult to a routing decision dict.

    DEV-251: Enables using HF zero-shot classifier results in the routing pipeline.
    DEV-251 Part 3.1: Added query parameter for follow-up detection.

    Args:
        hf_result: IntentResult from HFIntentClassifier.classify()
        query: Optional query text for follow-up pattern detection

    Returns:
        Routing decision dict compatible with LLM router format
    """
    # Map HF intent to RoutingCategory (they use the same string values)
    route = hf_result.intent

    # Determine if retrieval is needed based on route
    retrieval_routes = {"technical_research", "theoretical_definition", "golden_set"}
    needs_retrieval = route in retrieval_routes

    # DEV-251 Part 3.1: Detect follow-ups from query pattern
    is_followup = _detect_followup_from_query(query) if query else False

    return {
        "route": route,
        "confidence": hf_result.confidence,
        "reasoning": f"HuggingFace zero-shot classification (confidence: {hf_result.confidence:.2f})",
        "entities": [],  # HF classifier doesn't extract entities
        "requires_freshness": False,
        "suggested_sources": [],
        "needs_retrieval": needs_retrieval,
        "is_followup": is_followup,
    }
